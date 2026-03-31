# Implementation Plan

**Companion to:** [mvp-readiness.md](mvp-readiness.md)
**Last updated:** 2026-03-31
**Status:** All tasks implemented ✅

Tasks are ordered by priority tier. All items below have been implemented,
tested (139 tests passing), and are ready for review.

---

## P0 tasks — must complete before launch

### TASK-01 · Hash the Authorization header key in the rate limiter

**Priority:** P0-1
**Files to change:**
- `apps/gateway/gateway/presentation/http/middleware/rate_limit.py`
- `tests/apps/gateway/presentation/test_middleware.py`

**Problem:** The sliding-window `_buckets` dict is keyed by the raw
`Authorization` header value (`Bearer <raw_api_key>`). This stores every
active API key in the process heap.

**Implementation steps:**

1. In `rate_limit.py`, import `hashlib` at the top of the file.
2. Replace the bucket-key assignment:
   ```python
   # Before
   key = request.headers.get("Authorization") or (
       request.client.host if request.client else "unknown"
   )

   # After
   raw = request.headers.get("Authorization") or (
       request.client.host if request.client else "unknown"
   )
   key = hashlib.sha256(raw.encode()).hexdigest()
   ```
3. No change to the rest of the middleware logic.
4. In `test_middleware.py`, add a test asserting that two requests with
   the same Authorization header share the same bucket (i.e. rate-limiting
   still works correctly after the change).

**Done when:** Raw API key string no longer appears as a dict key; all existing
rate-limiter tests still pass; new test passes.

---

### TASK-02 · Add `/health/ready` readiness endpoint

**Priority:** P0-2
**Files to change:**
- `apps/gateway/gateway/presentation/http/schemas/health.py`
- `apps/gateway/gateway/presentation/http/routers/health.py`
- `apps/gateway/gateway/infrastructure/gateway_factory.py`
- `apps/gateway/gateway/application/ports/application_factory.py`
- `docker-compose.yml`
- `tests/apps/gateway/presentation/test_health_router.py`

**Problem:** There is no way for the reverse proxy or operator to verify that
the gateway is actually usable (DB connected, product key loaded, catalog
populated). A fresh deployment with an empty catalog silently serves
404s on every banking request.

**Note on current behaviour:** The factory `startup()` already raises
`InternalError` if no product registration is found — meaning the process
crashes at boot if the product key is missing. The readiness endpoint
complements this by providing a live check that operators and the reverse
proxy can poll at any time *after* boot.

**Implementation steps:**

1. **Schema** — add `ReadinessResponse` to `schemas/health.py`:
   ```python
   class ReadinessCheck(BaseModel):
       model_config = {"extra": "forbid"}
       db: str          # "ok" | "error"
       product_key: str # "loaded" | "missing"
       catalog: str     # "ok" (>0 institutes) | "empty"

   class ReadinessResponse(BaseModel):
       model_config = {"extra": "forbid"}
       status: str      # "ready" | "not_ready"
       checks: ReadinessCheck
   ```

2. **Factory** — expose a `check_readiness()` async method on
   `GatewayApplicationFactory` (and add it to the `ApplicationFactory`
   protocol):
   ```python
   async def check_readiness(self) -> dict[str, str]:
       checks: dict[str, str] = {}
       # DB ping
       try:
           async with self._engine.connect() as conn:
               await conn.execute(text("SELECT 1"))
           checks["db"] = "ok"
       except Exception:
           checks["db"] = "error"
       # Product key
       checks["product_key"] = (
           "loaded" if self._loaded_product_key else "missing"
       )
       # Catalog
       institutes = await self.caches.institute.list_all()
       checks["catalog"] = "ok" if institutes else "empty"
       return checks
   ```

3. **Router** — add the `/health/ready` route in `routers/health.py`:
   ```python
   from fastapi import Request
   from fastapi.responses import JSONResponse

   @router.get("/health/ready", response_model=ReadinessResponse)
   async def readiness(request: Request) -> JSONResponse:
       factory = get_factory()
       checks = await factory.check_readiness()
       all_ok = all(
           v in ("ok", "loaded") for v in checks.values()
       )
       body = ReadinessResponse(
           status="ready" if all_ok else "not_ready",
           checks=ReadinessCheck(**checks),
       )
       return JSONResponse(
           status_code=200 if all_ok else 503,
           content=body.model_dump(),
       )
   ```

4. **docker-compose.yml** — update the gateway health check to use
   `/health/ready` instead of `/health/live`:
   ```yaml
   healthcheck:
     test: ["CMD", "python", "-c",
            "import urllib.request, sys; r = urllib.request.urlopen('http://localhost:8000/health/ready'); sys.exit(0 if r.status == 200 else 1)"]
   ```

5. **Tests** — add tests to `test_health_router.py`:
   - `test_readiness_returns_200_when_all_checks_pass`
   - `test_readiness_returns_503_when_catalog_empty`
   - `test_readiness_returns_503_when_db_unreachable`

**Done when:** `GET /health/ready` returns 200 with `{"status": "ready"}` on
a fully initialised gateway and 503 on an uninitialised one; Docker Compose
health check uses the new endpoint.

---

### TASK-03 · Document and streamline operator onboarding

**Priority:** P0-3
**Files to change:**
- `docs/developer/getting-started.md`
- `docker-compose.yml` (optional automation sub-task, see below)

**Problem:** After `docker compose up`, the gateway starts but no banking
request will succeed because the institute catalog is empty and no product key
is configured. There is no visible "you must do this first" guidance.

**Implementation steps — documentation (required):**

1. Open `docs/developer/getting-started.md`.
2. Add a prominent **"Post-install checklist"** section at the top, before
   any other content, containing the exact commands an operator must run
   after first boot:
   ```
   ## Post-install checklist (run once after first boot)

   1. Set your FinTS product key:
      docker compose run --rm gateway-admin-cli \
        gw-admin product update <YOUR_PRODUCT_KEY> --product-version 1.0

   2. Populate the institute catalog:
      docker compose run --rm gateway-admin-cli \
        gw-admin catalog sync /data/fints_institute.csv

   3. Verify the gateway is ready:
      curl http://localhost:8000/health/ready
      # Expected: {"status":"ready", ...}
   ```
3. Make clear that step 3 blocks on TASK-02 being deployed first (or document
   the equivalent `inspect state` command as the fallback).

**Implementation steps — automation (optional, nice-to-have for MVP):**

4. Extend `docker-compose.yml` to add a `gateway-catalog-init` one-shot
   service that runs `gw-admin catalog sync` after `gateway-admin-cli`
   (the db-init service) completes **only if the catalog is empty**.
   This requires the catalog sync command to be idempotent when re-run
   (it already is — `replace_catalog` does DELETE + bulk INSERT in one
   transaction).

   ```yaml
   gateway-catalog-init:
     image: ... # same as gateway-admin-cli
     depends_on:
       gateway-admin-cli:
         condition: service_completed_successfully
     command: ["gw-admin", "catalog", "sync", "/data/fints_institute.csv"]
     volumes:
       - ./data:/data:ro
     env_file: config/admin_cli.env
   ```

**Done when:** A developer following `getting-started.md` from scratch reaches
`{"status":"ready"}` from `/health/ready` without needing to know anything
about FinTS or the internal architecture.

---

## P1 tasks — fix before production traffic

### TASK-04 · Add security response headers middleware

**Priority:** P1-1
**Independent — can be done at any time.**
**Files to change:**
- `apps/gateway/gateway/presentation/http/middleware/` (new file
  `security_headers.py`)
- `apps/gateway/gateway/presentation/http/api.py`
- `tests/apps/gateway/presentation/test_middleware.py`

**Implementation steps:**

1. Create
   `apps/gateway/gateway/presentation/http/middleware/security_headers.py`:
   ```python
   """Middleware that sets standard defence-in-depth response headers."""

   from __future__ import annotations

   from starlette.middleware.base import BaseHTTPMiddleware
   from starlette.requests import Request
   from starlette.responses import Response

   _SECURITY_HEADERS = {
       "X-Content-Type-Options": "nosniff",
       "X-Frame-Options": "DENY",
       "Referrer-Policy": "no-referrer",
   }


   class SecurityHeadersMiddleware(BaseHTTPMiddleware):
       async def dispatch(self, request: Request, call_next: object) -> Response:
           response: Response = await call_next(request)
           for header, value in _SECURITY_HEADERS.items():
               response.headers[header] = value
           return response
   ```

2. In `api.py`, import and register the middleware (add alongside the other
   `add_middleware` calls):
   ```python
   from .middleware.security_headers import SecurityHeadersMiddleware
   # ...
   app.add_middleware(SecurityHeadersMiddleware)
   ```

3. In `test_middleware.py`, add:
   ```python
   def test_security_headers_are_set_on_api_response() -> None:
       # Assert X-Content-Type-Options, X-Frame-Options, Referrer-Policy present
   ```

**Done when:** All three headers appear on every non-health and health response;
test passes.

---

### TASK-05 · Add missing test for 365-day transaction range cap

**Priority:** P1-2
**Independent — can be done at any time.**
**Files to change:**
- `tests/apps/gateway/application/test_fetch_transactions.py`

**Note:** The 365-day validation is **already implemented** in
`FetchTransactionsCommand._resolve_date_range`:
```python
if (end_date - start_date).days > 365:
    raise ValidationError("Date range must not exceed 365 days")
```
Only the corresponding test is missing.

**Implementation steps:**

1. In `test_fetch_transactions.py`, add one test after the existing
   `test_fetch_transactions_rejects_inverted_date_range`:
   ```python
   def test_fetch_transactions_rejects_range_exceeding_365_days() -> None:
       # start_date = today - 366 days, end_date = today
       # expect ValidationError with code GatewayErrorCode.VALIDATION_ERROR
   ```
2. Follow the same fixture pattern as the existing inverted-range test
   (use `FakeIdProvider`, `FakeInstituteCache`, etc.).

**Done when:** The new test passes; coverage of `_resolve_date_range` is
complete for all three validation branches (inverted, >365 days, valid).

---

## P2 tasks — post-MVP hardening

### TASK-06 · Integration tests for `gw-admin` CLI commands

**Priority:** P2-2
**Files to change / create:**
- `tests/apps/gateway_admin_cli/` (new test files)
- Reuse `tests/apps/gateway/conftest.py` PostgreSQL testcontainer fixtures

**Scope (start small — one test per command):**

| Command | Test name |
|---|---|
| `create user` | `test_create_user_generates_key_and_persists` |
| `disable user` | `test_disable_user_changes_status` |
| `rotate-key` | `test_rotate_key_issues_new_hash` |
| `catalog sync` | `test_catalog_sync_replaces_institutes` |
| `product update` | `test_product_update_persists_key` |

**Implementation steps:**

1. Create `tests/apps/gateway_admin_cli/__init__.py` and
   `tests/apps/gateway_admin_cli/conftest.py`. Import and re-export the
   `postgres_engine` and `async_runner` fixtures from the gateway conftest
   (or move them to a shared `tests/conftest.py`).
2. For each command, write an integration test that:
   - Instantiates the `ConcreteAdminFactory` pointed at the testcontainer DB
   - Calls the command's application-layer class directly (not via Typer CLI)
   - Asserts the expected DB state afterwards
3. Do not test the Typer CLI layer (`typer.testing.CliRunner`) — test the
   application commands directly. Typer wiring is simple enough to trust.

**Done when:** At least one integration test per command listed above passes
against a testcontainer PostgreSQL database in CI.

---

### TASK-07 · Test HTTPS enforcement in the banking connector

**Priority:** P2-3
**Independent — can be done at any time.**
**Files to change:**
- `tests/apps/gateway/infrastructure/test_connector.py`

**Implementation steps:**

1. Add a test that constructs a `FinTSInstitute` with
   `pin_tan_url = "http://insecure.bank.example"` (plain HTTP).
2. Call `connector.list_accounts(institute, credentials)` and assert that
   `BankUpstreamUnavailableError` is raised (not a generic exception).
3. Follow the existing `StubClientFactory` / `StubClient` pattern in the
   test file — no real FinTS connection needed.

**Done when:** The test passes; a future accidental removal of the HTTPS check
in the connector will produce a visible test failure instead of a silent
regression.

---

### TASK-08 · CI lint — detect placeholder credentials in env files

**Priority:** P2-4
**Independent — can be done at any time.**
**Files to change / create:**
- `.github/workflows/` or equivalent CI config (add a lint step), **or**
- `.pre-commit-config.yaml` (add a hook)

**Implementation steps:**

1. Add a CI step (or pre-commit hook) that fails if any non-`.example` env
   file in `config/` contains the `change_me` placeholder:
   ```bash
   # In CI (bash step):
   if grep -rn "change_me" config/ --include="*.env" \
          --exclude="*.example"; then
     echo "ERROR: placeholder 'change_me' found in an env file"
     exit 1
   fi
   ```
2. If using pre-commit, a simple `id: detect-placeholder-creds` hook with
   `language: pygrep` and the pattern `change_me` applied to `config/*.env`
   works.

**Done when:** Committing a `config/gateway.env` containing `change_me=...`
fails CI or pre-commit before the code is pushed.

---

## Sequencing summary

```
Week 1 (unblock G3):
  TASK-01  Rate limiter key hash         (30 min)
  TASK-02  /health/ready endpoint        (2–3 hrs)
  TASK-03  Onboarding docs + compose     (1–2 hrs)

Week 2 (harden):
  TASK-04  Security headers middleware   (30 min)  ← independent
  TASK-05  365-day range test            (15 min)  ← independent

Post-launch:
  TASK-06  Admin CLI integration tests   (half day)
  TASK-07  Connector HTTPS test          (20 min)
  TASK-08  CI credential lint            (30 min)
```
