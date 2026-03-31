# MVP Readiness — Issue Tracker & Prioritisation

**Last updated:** 2026-03-31
**Status:** Pre-launch assessment

---

## Summary

The core feature set is complete and the architecture is production-grade.
All five banking endpoints, the decoupled TAN flow, and the full `gw-admin`
CLI are implemented and tested. The estimate is ~85–90% of the way to a
production launch.

What remains are targeted fixes across three priority tiers documented below.

---

## 🔴 P0 — Must fix before launch

### P0-1 · Rate limiter stores raw API key in memory dict

**File:** `apps/gateway/gateway/presentation/http/middleware/rate_limit.py`

The sliding-window bucket key is the raw `Authorization` header value
(`Bearer <raw_api_key>`). This means every active API key is present as a
Python dict key in the live process heap. A heap dump, crash report, or
debugger session on a production process would expose all active keys.

**Fix:** Hash the Authorization header with a truncated HMAC-SHA256 (or even
a plain `hashlib.sha256`) before using it as the bucket key. Per-consumer
isolation is preserved; the secret never appears in the dict.

```python
import hashlib

raw = request.headers.get("Authorization") or (request.client.host ...)
key = hashlib.sha256(raw.encode()).hexdigest()
```

---

### P0-2 · No `/health/ready` readiness endpoint

**File:** `apps/gateway/gateway/presentation/http/routers/health.py`

`/health/live` returns `{"status": "ok"}` unconditionally as long as the
process is running. There is no way for the reverse proxy or operator to
detect:

- Database connectivity failure
- Missing product registration (no product key → every banking call fails)
- Empty institute catalog (catalog sync not yet run → every banking call
  returns 404 "Institution not found")

This makes fresh deployments silently broken in a confusing way.

**Fix:** Add a `GET /health/ready` endpoint that:
1. Issues a lightweight DB ping (e.g. `SELECT 1`)
2. Checks that a product registration exists in the cache / DB
3. Checks that at least one institute is loaded in the institute cache

Return `200 {"status": "ready"}` only when all three pass; return
`503 {"status": "not_ready", "reason": "..."}` otherwise. Update the Docker
Compose health check to poll `/health/ready`.

---

### P0-3 · Operator onboarding gap — catalog and product key not initialised automatically

**File:** `docker-compose.yml`

The compose file runs `gw-admin db init` automatically as part of startup,
but does **not** run `catalog sync` or set a product key. A completely fresh
deployment ends up with:

- Empty institute catalog
- No product registration

Every banking request will fail (see P0-2). This breaks PRD goal G3 ("deploy
in under 30 minutes").

**Fix options (choose one or both):**

1. **Automated:** Mount `data/fints_institute.csv` into the admin-cli
   container and extend the init command (or add a `db seed` command) that
   runs catalog sync if the catalog is empty.
2. **Documented:** Add a clearly visible "post-install checklist" at the top
   of [getting-started.md](getting-started.md) that lists exactly:
   - `gw-admin product update <key> --product-version 1.0`
   - `gw-admin catalog sync data/fints_institute.csv`
   - `gw-admin inspect state` to verify before starting traffic

Option 2 alone is sufficient for MVP; option 1 is a better experience.

---

## 🟡 P1 — Fix before promoting to production traffic

### P1-1 · Missing security response headers

**File:** `apps/gateway/gateway/presentation/http/api.py` (new middleware)

The middleware stack does not set any of the standard defence-in-depth
response headers. While the gateway is a pure JSON API (no HTML, no cookies),
these headers affect security scanner reports and compliance baselines.

**Missing headers:**

| Header | Value |
|---|---|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `no-referrer` |

**Fix:** Add a single `SecurityHeadersMiddleware` (similar in structure to
`CacheControlMiddleware`) that appends these three headers on every response.
~15 lines of code.

---

### P1-2 · 365-day transaction range cap not enforced at the API boundary

**File:** `apps/gateway/gateway/application/banking/commands/fetch_transactions.py`
and `apps/gateway/gateway/presentation/http/schemas/transactions.py`

The PRD states "Max 365-day range" but neither the presentation schema nor the
application command validates this. A caller can pass an arbitrary range that
will be forwarded to the bank, potentially causing unexpected bank-side errors
or long-running requests.

**Fix:** In `FetchTransactionsCommand.__call__`, after the date-range
inversion check, add:

```python
if (end_date - start_date).days > 365:
    raise ValidationError("Date range must not exceed 365 days")
```

Add a corresponding test in
`tests/apps/gateway/application/test_fetch_transactions.py`.

---

## 🟢 P2 — Post-MVP / hardening backlog

### P2-1 · Bank credentials in pending operation session state

**Context:** Note in repo memory; to be tackled as a separate effort.

During a pending decoupled-TAN flow the bank `user_id` and `password` (PIN)
are serialised as plaintext JSON into the `session_state: bytes` blob stored
in `InMemoryOperationSessionStore` (TTL 120 s). This is architecturally
necessary because the resume worker must rebuild the FinTS session.

In the single-instance MVP this is acceptable — the state is never persisted
and is wiped on terminal transition. It must be addressed before moving to a
multi-instance or fully managed deployment (e.g. Redis-backed session store).

**Tracked separately.**

---

### P2-2 · `gw-admin` CLI has no automated tests

The admin application and infrastructure layers (create/disable/delete/
rotate user, catalog sync, product update) have no unit or integration tests.
All gateway tests exercise the read-side paths; the admin write paths are
covered only by the domain model tests for `ApiConsumer`.

**Fix (iterative):** Add at least one happy-path integration test per admin
command using a testcontainer PostgreSQL fixture (the fixture already exists
in `tests/apps/gateway/conftest.py` and can be reused from
`tests/apps/gateway_admin_cli/`).

---

### P2-3 · No test for HTTPS enforcement in the connector

**File:** `tests/apps/gateway/infrastructure/test_connector.py`

The connector correctly rejects `pin_tan_url` values that do not start with
`https://`, but there is no test asserting this behaviour. A regression would
silently allow HTTP bank connections in production.

**Fix:** Add a test that constructs a `FinTSInstitute` with
`pin_tan_url = "http://bank.example.com"` and asserts that the connector
raises `BankUpstreamUnavailableError`.

---

### P2-4 · CI lint — detect `change_me` placeholder in non-example env files

`config/admin_cli.env.example` and `config/gateway.env.example` use
`change_me` as placeholder passwords. There is no guard preventing an
operator from accidentally copying these verbatim for a production deployment.

**Fix:** Add a CI step (or a pre-commit hook) that runs:

```bash
grep -rn "change_me" config/*.env && exit 1 || exit 0
```

Fails fast if an actual `.env` file (not `.env.example`) contains the
placeholder.

---

### P2-5 · TOCTOU window in `InMemoryOperationSessionStore` during bulk resume

**File:** `apps/gateway/gateway/application/banking/commands/resume_pending_operations.py`

`list_all()` is called and then `update()` / `delete()` are called per session
in a loop, without holding the store lock across the full iteration.
Under the single-worker MVP constraint this is harmless. It becomes a
correctness issue when parallelism is introduced (multiple resume workers or
concurrent requests touching the same session).

**Track alongside P2-1 (session store backend replacement).**

---

## Closed / Won't Fix

| Item | Rationale |
|---|---|
| `GATEWAY_HOST` defaults to `0.0.0.0` | Intentional — the gateway is always reverse-proxied in production. |
| FinTS product key stored plaintext in PostgreSQL | Accepted risk — DB access is independently protected; application-layer encryption is not required for MVP. |
