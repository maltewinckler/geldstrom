---
description: "Run the full deployment check: docker compose up, verify admin UI on port 8001, sync catalog, create user if needed, update API key in .env, verify with geldstrom-cli, check all lookup endpoints (auth-protected), fetch transactions via the decoupled 2FA flow, and verify the audit trail"
name: "Deployment Check"
agent: "agent"
---

Run the full geldstrom deployment check sequence. Execute each step in order and stop if any step fails.

## Steps

### 1. Docker Compose Build
Run `docker compose build` to confirm there is nothing to build (no build sections expected).

### 2. Docker Compose Up
Run `docker compose up -d` and confirm all four containers reach the expected states:
- `geldstrom_postgres` — healthy
- `geldstrom_redis` — healthy
- `geldstrom_gateway_admin` — running (FastAPI admin UI on 127.0.0.1:8001)
- `geldstrom_gateway` — running

Verify with:
```bash
docker compose ps
```

### 3. Sync the FinTS Institute Catalog
The catalog is uploaded via the admin UI or via the API. Use the API directly:
```bash
curl -s -X POST http://localhost:8001/admin/catalog/sync \
  -F "file=@data/fints_institute.csv" | python3 -m json.tool
```
Expected response shape:
```json
{"loaded_count": 16000, "skipped_count": 0}
```

Check the gateway health endpoint (`curl -s http://localhost:8000/health/ready`) — `catalog` must be `"ok"` before proceeding.

If the readiness response reports `"product_key":"missing"`, verify that
`FINTS_PRODUCT_REGISTRATION_KEY` is set in `config/admin_cli.env`. The admin
service applies the product key automatically on startup from the env file.
Restart the service and re-check readiness:
```bash
docker compose restart gateway-admin
curl -s http://localhost:8000/health/ready
```

### 4. Create a User (if none exist)
List users via the admin API:
```bash
curl -s http://localhost:8001/admin/users | python3 -m json.tool
```
If `"total": 0`, create a user via the admin CLI inside the running container:
```bash
docker compose exec gateway-admin gw-admin users create malte@example.com
```
Capture the raw API key printed (shown once). The key is also sent by email if SMTP is configured.

### 5. Update API Key in `.env`
Open [`.env`](../../.env) and replace the `GATEWAY_API_KEY` value with the newly generated key.

### 6. Verify Gateway is Ready
```
curl -s http://localhost:8000/health/ready
```
Expected: `{"status":"ready","checks":{"db":"ok","product_key":"loaded","catalog":"ok"}}`

### 7. Test with geldstrom-cli
Activate the venv and run the following CLI commands against the live gateway:

```bash
source .venv/bin/activate
geldstrom-cli health   --env-file .env
geldstrom-cli accounts --env-file .env
```

Both must succeed without errors. Report the results.

### 7b. Verify the BLZ Lookup and Bank List Endpoints

Read the API key from `.env`:
```bash
API_KEY=$(grep GATEWAY_API_KEY .env | cut -d= -f2 | tr -d '"')
```

**Single BLZ lookup — expects 200 (API key required):**
```bash
curl -s -H "Authorization: Bearer $API_KEY" \
  http://localhost:8000/v1/lookup/10010010 | python3 -m json.tool
```
Expected response shape:
```json
{
  "blz": "10010010",
  "bic": "PBNKDEFFXXX",
  "name": "Postbank",
  "organization": "BdB",
  "is_fints_capable": true
}
```

**Single BLZ lookup without API key — expects 401:**
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/v1/lookup/10010010
```
Expected: `401`

**Unknown BLZ — expects 404:**
```bash
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $API_KEY" \
  http://localhost:8000/v1/lookup/00000000
```
Expected: `404`

**Invalid format — expects 422:**
```bash
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $API_KEY" \
  http://localhost:8000/v1/lookup/INVALID
```
Expected: `422`

**All-banks list — expects 200 with `banks` array (API key required):**
```bash
curl -s -H "Authorization: Bearer $API_KEY" \
  http://localhost:8000/v1/lookup | python3 -m json.tool | head -20
```
Expected response shape:
```json
{
  "banks": [
    {
      "blz": "...",
      "bic": "...",
      "name": "...",
      "organization": "...",
      "is_fints_capable": true
    },
    ...
  ]
}
```
Report the total number of entries: `curl -s -H "Authorization: Bearer $API_KEY" http://localhost:8000/v1/lookup | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d['banks']), 'banks')"`.

**All-banks list without API key — expects 401:**
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/v1/lookup
```
Expected: `401`

All checks must match the expected status codes.

### 8. Rebuild Docker images (when code has changed)

If any source files under `packages/geldstrom/` or `apps/gateway/` have been
modified since the last image was built, rebuild the gateway before testing:

```bash
docker build -f apps/gateway/Dockerfile -t maltewin/geldstrom-gateway:latest .
docker compose up -d --force-recreate gateway
```

If any source files under `apps/gateway_admin/` have been modified, rebuild
the admin UI image (frontend is built inside the Dockerfile):

```bash
docker build -f apps/gateway_admin/Dockerfile -t maltewin/geldstrom-gateway-admin:latest .
docker compose up -d --force-recreate gateway-admin
```

Then re-check `curl -s http://localhost:8000/health/ready` until it reports all
checks `"ok"` before proceeding.

### 9. Fetch Transactions and Verify Decoupled 2FA Flow

This step fetches real transaction history and specifically tests that the `FinTS3ClientDecoupled` gateway returns **202 immediately** instead of blocking for up to 120 seconds, and that the CLI polls the bank correctly until TAN approval.

#### 9a. Happy path via geldstrom-cli (preferred)

Get a valid IBAN from the accounts listing, then fetch transactions with a 280-day window. The CLI will automatically:
1. POST the request — gateway responds 202 in a few seconds
2. Print "⏳ 2FA required" and start polling the bank every 5 s
3. Return the full transaction table once you approve the TAN

```bash
source .venv/bin/activate
geldstrom-cli accounts --env-file .env          # note an IBAN from the output
geldstrom-cli transactions <IBAN> --days 280 --env-file .env
```

**Expected:** The command completes with a transaction table containing entries from the last 280 days. If the request blocks for more than ~5 s before printing "⏳ 2FA required", the decoupled flow is broken.

#### 9b. Manual fallback (use only if the CLI command above fails)

```bash
API_KEY=$(grep GATEWAY_API_KEY .env | cut -d= -f2 | tr -d '"')
BLZ=$(grep FINTS_BLZ .env | cut -d= -f2 | tr -d '"')
USER_ID=$(grep FINTS_USER .env | cut -d= -f2 | tr -d '"')
PIN=$(grep FINTS_PIN .env | cut -d= -f2 | tr -d '"')
TAN_METHOD=$(grep FINTS_TAN_METHOD .env | cut -d= -f2 | tr -d '"')
TAN_MEDIUM=$(grep FINTS_TAN_MEDIUM .env | cut -d= -f2 | tr -d '"')
START_DATE=$(date -d "280 days ago" +%Y-%m-%d)
END_DATE=$(date +%Y-%m-%d)
IBAN="<replace-with-iban-from-accounts>"

time curl -s -o /tmp/txn_202.json -w "HTTP %{http_code}\n" \
  -X POST http://localhost:8000/v1/banking/transactions \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"protocol\":\"fints\",\"blz\":\"$BLZ\",\"user_id\":\"$USER_ID\",
       \"password\":\"$PIN\",\"iban\":\"$IBAN\",
       \"start_date\":\"$START_DATE\",\"end_date\":\"$END_DATE\",
       \"tan_method\":\"$TAN_METHOD\",\"tan_medium\":\"$TAN_MEDIUM\"}"

cat /tmp/txn_202.json
```

**Expected:** HTTP 202 returned **within a few seconds**, with body:
```json
{
  "status": "pending_confirmation",
  "operation_id": "<uuid>",
  "expires_at": "<timestamp>",
  "polling_interval_seconds": 5
}
```

**Failure condition:** If the request blocks for more than 10 seconds or returns
HTTP 200 without going through 2FA, the `FinTS3ClientDecoupled` integration is
broken (likely a missing `challenge_handler` being passed to `dialog.send()`).

Then approve the TAN in your banking app and poll the operation until it
reaches a terminal state, using the active poll endpoint (which re-submits
credentials to resume the bank dialog):

```bash
OP_ID=$(cat /tmp/txn_202.json | python3 -c "import sys,json; print(json.load(sys.stdin)['operation_id'])")
curl -s -X POST http://localhost:8000/v1/banking/operations/$OP_ID/poll \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"protocol\":\"fints\",\"blz\":\"$BLZ\",\"user_id\":\"$USER_ID\",\"password\":\"$PIN\",\"tan_method\":\"$TAN_METHOD\",\"tan_medium\":\"$TAN_MEDIUM\"}" \
  | python3 -m json.tool
```

**Expected:** After TAN approval the poll returns `"status": "completed"` with
a `result_payload.transactions` list.

### 10. Verify Audit Trail and Integrity

This step confirms that the audit service is persisting events correctly (i.e. the `GRANT INSERT ON audit_events` regression is not present) and that the trail is tamper-evident (DELETE is blocked by the database trigger).

#### 10a. Confirm audit events were recorded

Fetch the recent audit log from the admin API:
```bash
curl -s "http://localhost:8001/admin/audit?page_size=10" | python3 -m json.tool
```

Expected response shape:
```json
{
  "events": [
    {
      "event_id": "<uuid>",
      "event_type": "consumer_authenticated",
      "consumer_id": "<uuid>",
      "occurred_at": "<timestamp>"
    }
  ],
  "total": <N>,
  "page": 1,
  "page_size": 10
}
```

**Requirements:**
- `total` must be **≥ 1** — at least one `consumer_authenticated` event must exist from the `geldstrom-cli accounts` call in step 7. If `total` is 0 this is the `GRANT INSERT` regression.
- Every event must have a non-null `event_id`, `event_type`, and `occurred_at`.
- The `consumer_id` field may be `null` only for `consumer_auth_failed` events (unknown key); it must be a UUID for `consumer_authenticated`.

Report the total event count and the event types present.

#### 10b. Filter by event type

Verify that filtering works and that authentication events are properly typed:
```bash
curl -s "http://localhost:8001/admin/audit?event_type=consumer_authenticated&page_size=5" \
  | python3 -m json.tool
```

Expected: only `"event_type": "consumer_authenticated"` entries in the `events` array.

#### 10c. Verify the delete-prevention trigger (tamper-evidence)

Attempt to delete an audit row directly via the PostgreSQL superuser — this **must fail**:
```bash
docker compose exec postgres psql -U postgres -d geldstrom \
  -c "DELETE FROM audit_events WHERE event_id = (SELECT event_id FROM audit_events LIMIT 1);" 2>&1
```

Expected output contains: `ERROR:  Deletion from audit_events is not permitted`

If the DELETE succeeds without error, the tamper-prevention trigger is missing or broken.

#### 10d. Confirm the gateway user cannot delete audit events

Verify the gateway DB user (read-only except for INSERT) also cannot delete:
```bash
GW_PASS=$(grep GATEWAY_DB_PASSWORD config/gateway.env | cut -d= -f2 | tr -d '"')
docker compose exec postgres psql \
  "postgresql://gateway:${GW_PASS}@localhost/geldstrom" \
  -c "DELETE FROM audit_events;" 2>&1
```

Expected: either the trigger error (`Deletion from audit_events is not permitted`) if rows exist, or a privilege error if the trigger fires first. Either outcome confirms the trail cannot be silently cleared by the application user.
