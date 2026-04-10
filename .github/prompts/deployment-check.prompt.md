---
description: "Run the full deployment check: docker compose up, sync catalog, create user if needed, update API key in .env, verify with geldstrom-cli, check all lookup endpoints (auth-protected), and fetch transactions via the decoupled 2FA flow"
name: "Deployment Check"
agent: "agent"
---

Run the full geldstrom deployment check sequence. Execute each step in order and stop if any step fails.

## Steps

### 1. Docker Compose Build
Run `docker compose build` to confirm there is nothing to build (no build sections expected).

### 2. Docker Compose Up
Run `docker compose up -d` and confirm all three containers reach the expected states:
- `geldstrom_postgres` — healthy
- `geldstrom_gateway_admin_cli` — exited (0)
- `geldstrom_gateway` — running

### 3. Sync the FinTS Institute Catalog
Run:
```
docker compose run --rm gateway-admin-cli gw-admin catalog sync /data/fints_institute.csv
```
Check the gateway health endpoint (`curl -s http://localhost:8000/health/ready`) — `catalog` must be `"ok"` before proceeding.

If the readiness response reports `"product_key":"missing"`, verify that
`FINTS_PRODUCT_REGISTRATION_KEY` is set in `config/admin_cli.env` or run:
```
docker compose run --rm gateway-admin-cli gw-admin product update "<YOUR_PRODUCT_KEY>" --product-version "1.0.0"
```
Then re-check readiness before proceeding.

### 4. Create a User (if none exist)
Run:
```
docker compose run --rm gateway-admin-cli gw-admin users list
```
If the table is empty, create one:
```
docker compose run --rm gateway-admin-cli gw-admin users create malte@example.com
```
Capture the raw API key printed (shown once).

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

### 8. Rebuild Docker image (when code has changed)

If any source files under `packages/geldstrom/` or `apps/gateway/` have been
modified since the last image was built, rebuild before testing:

```bash
docker build -f apps/gateway/Dockerfile -t maltewin/geldstrom-gateway:latest .
docker compose up -d --force-recreate gateway
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
