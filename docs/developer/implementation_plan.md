# Gateway Implementation Plan

This plan translates `api_architecture.md` into a concrete, ordered sequence of implementation steps.

The rule is: **domain first, application second, infrastructure third, presentation last.**

Each phase is fully testable in isolation before the next phase begins. No phase skips ahead to infrastructure before the application layer is working against fakes.

---

## Phase 0 — Workspace scaffolding

Goal: the gateway service app and admin CLI app exist in the monorepo, are resolvable by uv, and can each be imported.

### 0.1 — Create `apps/gateway`

Files to create:

```text
apps/gateway/
├── pyproject.toml
├── README.md
└── gateway/
    └── __init__.py
```

`pyproject.toml` dependencies:

```toml
[project]
name = "gateway"
dependencies = [
    "geldstrom",
  "fastapi>=0.115",
  "uvicorn[standard]>=0.32",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.29",
    "argon2-cffi>=23.1",
    "cryptography>=42.0",
]
```

### 0.2 — Create `apps/gateway_admin_cli`

Files to create:

```text
apps/gateway_admin_cli/
├── pyproject.toml
├── README.md
└── gateway_admin_cli/
  └── __init__.py
```

`pyproject.toml` dependencies:

```toml
[project]
name = "gateway-admin-cli"
dependencies = [
    "gateway",
  "typer>=0.15",
  "rich>=13.0",
]
```

### 0.3 — Register workspace sources in root `pyproject.toml`

Add entries under `[tool.uv.sources]`:

```toml
gateway = { workspace = true }
gateway-admin-cli = { workspace = true }
```

Add entries under `[tool.ruff] src`:

```toml
src = ["packages", "apps", "tests"]
```

### 0.4 — Create test directories

```text
tests/apps/gateway/
tests/apps/gateway_admin_cli/
```

Each needs an `__init__.py`.

### Done when

- `uv lock` resolves without errors
- `uv run python -c "import gateway, gateway_admin_cli"` succeeds

---

## Phase 1 — Domain layer

Goal: all domain aggregates, value objects, domain services, and repository/connector port interfaces exist as pure Python with no framework dependencies. Every public invariant is covered by a unit test.

Work only in `gateway/domain/`.

### 1.1 — Shared domain primitives

File: `gateway/domain/shared/`

- `EntityId` base value object (wraps UUID, frozen dataclass or similar)
- `DomainError` base exception class
- `BankProtocol` enum with `FINTS = "fints"` as the initial member

### 1.2 — Consumer access domain

File: `gateway/domain/consumer_access/`

Value objects:

- `ConsumerId(EntityId)`
- `EmailAddress` — validates RFC 5321 local part and domain, case-folds on construction
- `ApiKeyHash` — wraps string, no plaintext method
- `ConsumerStatus` — enum: `ACTIVE`, `DISABLED`, `DELETED`

Aggregate:

- `ApiConsumer`
  - fields: `consumer_id`, `email`, `api_key_hash`, `status`, `created_at`, `rotated_at`
  - invariants enforced in `__init__` or factory method:
    - active consumers must have a key hash
    - deleted consumers cannot be re-activated directly

Domain service:

- `ApiKeyVerifier.verify(presented_key: str, stored_hash: ApiKeyHash) -> bool`
  - pure function, no side effects, no infrastructure
  - verification uses Argon2id against a stored PHC hash; authentication works by scanning active cached consumers and verifying until one matches

Repository port:

- `ApiConsumerRepository` (abstract base class or Protocol)
  - `async get_by_id(consumer_id: ConsumerId) -> ApiConsumer | None`
  - `async get_by_email(email: EmailAddress) -> ApiConsumer | None`
  - `async list_all_active() -> list[ApiConsumer]`
  - `async save(consumer: ApiConsumer) -> None`

Tests: `tests/apps/gateway/domain/test_consumer_access.py`

- `ApiConsumer` invariants
- `EmailAddress` validation (valid, invalid, case folding)
- `ApiKeyVerifier` returns correct bool (use a known hash fixture)

### 1.3 — Institution catalog domain

File: `gateway/domain/institution_catalog/`

Value objects:

- `BankLeitzahl` — validates 8-digit numeric string
- `Bic` — validates 8 or 11 character alphanumeric string
- `InstituteEndpoint` — wraps a URL string, validates scheme is https

Aggregate:

- `FinTSInstitute`
  - fields: `blz`, `bic`, `name`, `city`, `organization`, `pin_tan_url`, `fints_version`, `last_source_update`, `source_row_checksum`, `source_payload`
  - `pin_tan_url` may be None for institutes that do not support PIN/TAN
  - `is_pin_tan_capable() -> bool`

Domain service:

- `InstituteSelectionPolicy.select(candidates: list[FinTSInstitute]) -> FinTSInstitute`
  - Rule 1: prefer rows where `is_pin_tan_capable()` is True
  - Rule 2: among those, prefer the row with the most recent `last_source_update`
  - Rule 3: if still tied, prefer the row with the lexicographically smallest `source_row_checksum` (deterministic tiebreak)

Repository port:

- `FinTSInstituteRepository` (Protocol)
  - `async get_by_blz(blz: BankLeitzahl) -> FinTSInstitute | None`
  - `async list_all() -> list[FinTSInstitute]`
  - `async replace_catalog(institutes: list[FinTSInstitute]) -> None`

Tests: `tests/apps/gateway/domain/test_institution_catalog.py`

- `BankLeitzahl` validation
- `InstituteSelectionPolicy` with all three tiebreak scenarios

### 1.4 — Product registration domain

File: `gateway/domain/product_registration/`

Value objects:

- `EncryptedProductKey` — wraps bytes, no plaintext accessor
- `ProductVersion` — wraps string
- `KeyVersion` — wraps string

Aggregate:

- `FinTSProductRegistration`
  - fields: `registration_id`, `encrypted_product_key`, `product_version`, `key_version`, `updated_at`
  - no plaintext accessor; decryption is the responsibility of the crypto infrastructure service

Repository port:

- `FinTSProductRegistrationRepository` (Protocol)
  - `async get_current() -> FinTSProductRegistration | None`
  - `async save_current(registration: FinTSProductRegistration) -> None`

Tests: `tests/apps/gateway/domain/test_product_registration.py`

- aggregate construction
- value object invariants

### 1.5 — Banking gateway domain

File: `gateway/domain/banking_gateway/`

Value objects (all frozen, all transient):

- `PresentedBankCredentials` — groups `PresentedBankUserId`, `PresentedBankPassword`, `BankLeitzahl`, `BankProtocol`
- `PresentedBankUserId` — wraps `SecretStr`
- `PresentedBankPassword` — wraps `SecretStr`
- `RequestedIban` — wraps `SecretStr`, validates basic IBAN format
- `AuthenticatedConsumer` — minimal identity: `consumer_id`, `email`

Using `SecretStr` in these gateway-owned domain value objects is intentional.

The goal is to keep plaintext exposure delayed as long as possible while still keeping the value objects explicit in the domain model.

Operation state enum:

- `OperationStatus`: `PENDING_CONFIRMATION`, `COMPLETED`, `FAILED`, `EXPIRED`

Domain service:

- `BankRequestSanitizationPolicy.sanitize(credentials: PresentedBankCredentials) -> None`
  - raises `DomainError` if any field's `get_secret_value()` is an empty string
  - this is the only place `get_secret_value()` is called in the domain

Banking connector port:

- `BankingConnector` (Protocol)
  - `async list_accounts(credentials: PresentedBankCredentials) -> AccountsResult`
  - `async fetch_transactions(credentials: PresentedBankCredentials, iban: RequestedIban, start_date: date, end_date: date) -> TransactionsResult`
  - `async get_tan_methods(credentials: PresentedBankCredentials) -> TanMethodsResult`
  - `async resume_operation(session_state: bytes) -> ResumeResult`
- Result types are dataclasses in this file; they are gateway-owned, not Geldstrom types

The connector resolves the current product key internally through an infrastructure-only product key provider.

That keeps the shared FinTS product key out of public use case signatures and out of presentation-layer visibility.

Operation session store port:

- `OperationSessionStore` (Protocol)
  - `async create(session: PendingOperationSession) -> None`
  - `async get(operation_id: str) -> PendingOperationSession | None`
  - `async update(session: PendingOperationSession) -> None`
  - `async delete(operation_id: str) -> None`
  - `async expire_stale(now: datetime) -> int`

`PendingOperationSession` dataclass:

- `operation_id: str`
- `consumer_id: ConsumerId`
- `protocol: BankProtocol`
- `operation_type: Literal["accounts", "transactions", "tan_methods"]`
- `session_state: bytes`  — opaque, contains whatever the banking connector needs to resume
- `status: OperationStatus`
- `created_at: datetime`
- `expires_at: datetime`
- `last_polled_at: datetime | None`
- `result_payload: dict | None`  — populated on completion
- `failure_reason: str | None`  — populated on failure

Tests: `tests/apps/gateway/domain/test_banking_gateway.py`

- `BankRequestSanitizationPolicy` raises on empty fields
- `RequestedIban` validates format correctly

### Done when

- all domain tests pass
- `uv run pytest tests/apps/gateway/domain/` is green
- no import of FastAPI, SQLAlchemy, asyncpg, or geldstrom in any domain file

---

## Phase 2 — Application use cases (against fakes)

Goal: all use cases are implemented and tested using fake (in-memory) implementations of every port. No real infrastructure. No Geldstrom calls.

Work only in `gateway/application/`.

### 2.1 — Common application layer

File: `gateway/application/common/`

- `ApplicationError` base exception (maps to gateway error codes)
- `GatewayErrorCode` enum with all error code strings from the spec
- `ApplicationError` subclasses: `UnauthorizedError`, `ForbiddenError`, `InstitutionNotFoundError`, `BankAuthenticationFailedError`, `OperationNotFoundError`, `OperationExpiredError`, `BankUpstreamUnavailableError`, `UnsupportedProtocolError`, `InternalError`
- `IdProvider` protocol: `new_operation_id() -> str`, `now() -> datetime`

### 2.2 — `AuthenticateConsumer` use case

File: `gateway/application/consumer_access/authenticate_consumer.py`

Inputs: `presented_key: str`

Behavior:

- iterate over active consumers from the consumer cache
- call `ApiKeyVerifier.verify` against each cached consumer until one matches
- if no consumer matches, raise `UnauthorizedError`
- if the matching consumer is disabled, raise `ForbiddenError`
- return `AuthenticatedConsumer`

Cache port used here:

- `ConsumerCachePort` (Protocol): `async list_active() -> list[ApiConsumer]`

Rationale:

- Argon2id hashes are salted and non-deterministic, so there is no stable lookup key derived from the presented API key
- scanning the in-memory active-consumer cache is the simplest correct v1 design
- this remains efficient as long as the active consumer count stays within a modest operational range

Tests: `tests/apps/gateway/application/test_authenticate_consumer.py`

- valid key returns identity
- unknown consumer raises `UnauthorizedError`
- wrong key raises `UnauthorizedError`
- disabled consumer raises `ForbiddenError`

### 2.3 — `ListAccounts` use case

File: `gateway/application/banking_gateway/list_accounts.py`

Behavior:

1. authenticate consumer (delegate to `AuthenticateConsumer`)
2. validate credentials with `BankRequestSanitizationPolicy`
3. resolve institute from catalog cache; raise `InstitutionNotFoundError` if not found
4. ensure current product key material is available through the internal product key provider; raise `InternalError` if not loaded
5. call `BankingConnector.list_accounts`
6. if result is `decoupled_required`, create `PendingOperationSession` in the session store; return session id and expiry
7. if result is `completed`, return account list

Tests: fake connector returns both completed and decoupled variants.

### 2.4 — `FetchHistoricalTransactions` use case

File: `gateway/application/banking_gateway/fetch_transactions.py`

Behavior: mirrors `ListAccounts` but passes IBAN and date range. Default date range is today − 90 days through today when not supplied.

Tests: same pattern. Add a test that the 90-day default is applied correctly.

### 2.5 — `GetAllowedTanMethods` use case

File: `gateway/application/banking_gateway/get_tan_methods.py`

Behavior: mirrors `ListAccounts`. After getting methods from connector, filter to decoupled-compatible methods only before returning.

Tests: connector returns mixed methods; only decoupled ones appear in the result.

### 2.6 — `GetOperationStatus` use case

File: `gateway/application/banking_gateway/get_operation_status.py`

Behavior:

1. authenticate consumer
2. load session from store; raise `OperationNotFoundError` if absent
3. verify `session.consumer_id == authenticated.consumer_id`; raise `ForbiddenError` otherwise
4. return current status (pending, completed, failed, expired)
5. when returning completed result, remove the session from the store

### 2.7 — `ResumePendingOperations` background use case

File: `gateway/application/operation_sessions/resume_pending_operations.py`

Behavior:

1. list all sessions with status `PENDING_CONFIRMATION`
2. call `BankingConnector.resume_operation` for each
3. update session status accordingly
4. mark expired sessions as `EXPIRED` if `now > expires_at`

This is called by a background task, not an HTTP handler.

### 2.8 — `EvaluateHealth` use case

File: `gateway/application/health/evaluate_health.py`

- liveness: always returns `{status: "ok"}`
- readiness: checks each cache/store/crypto via injected health check ports; returns map of component → ok/failed and overall status

### 2.9 — Administration use cases

File: `gateway/application/administration/`

One file per use case:

- `sync_institute_catalog.py` — parses CSV path, normalizes, resolves duplicates, replaces catalog, refreshes cache
- `create_api_consumer.py` — generates key, hashes with Argon2id, persists, refreshes cache, returns raw key once
- `update_api_consumer.py` — updates mutable consumer metadata such as email, persists, refreshes cache
- `list_api_consumers.py` — returns consumer summaries with no secret fields
- `rotate_api_consumer_key.py` — replaces key hash, persists, refreshes cache, returns raw key once
- `disable_api_consumer.py`
- `delete_api_consumer.py`
- `update_product_registration.py` — encrypts new key, persists, refreshes cache
- `inspect_backend_state.py` — returns sanitized health and cache size info

Tests for all administration use cases: `tests/apps/gateway/application/test_administration.py`

### Done when

- `uv run pytest tests/apps/gateway/application/` is green
- no import of SQLAlchemy, asyncpg, FastAPI, or geldstrom in any application file

---

## Phase 3 — Infrastructure: crypto services

Goal: product key encryption/decryption and API key hashing are working independently of any database. These are needed before the persistence layer can be tested.

Work in `gateway/infrastructure/crypto/`.

### 3.1 — API key generation and hashing

File: `gateway/infrastructure/crypto/api_key_service.py`

- `ApiKeyService.generate() -> str` — returns a URL-safe random string of at least 32 bytes
- `ApiKeyService.hash(raw_key: str) -> ApiKeyHash` — Argon2id, PHC format output
- `ApiKeyService.verify(raw_key: str, stored_hash: ApiKeyHash) -> bool`

Parameters: time_cost, memory_cost, parallelism loaded from config, with documented defaults.

Tests: `tests/apps/gateway/infrastructure/test_crypto.py`

- hash → verify round-trip
- wrong key fails verification
- two calls to `generate()` produce different values

### 3.2 — Product key encryption

File: `gateway/infrastructure/crypto/product_key_service.py`

- `ProductKeyService.encrypt(plaintext: str) -> EncryptedProductKey` — AES-256-GCM, random nonce prepended to ciphertext
- `ProductKeyService.decrypt(encrypted: EncryptedProductKey) -> str`
- master key loaded from environment variable at construction time

Tests: encrypt → decrypt round-trip; wrong master key fails decryption.

---

## Phase 4 — Infrastructure: persistence

Goal: three PostgreSQL repository implementations exist and are tested against a real test database.

Work in `gateway/infrastructure/persistence/postgres/`.

Test setup: use a local PostgreSQL database (can be a Docker container) configured in `tests/apps/gateway/conftest.py`. Mark these tests with `@pytest.mark.integration` and skip if the database is not available.

### 4.1 — Database connection

File: `gateway/infrastructure/persistence/postgres/connection.py`

- async SQLAlchemy engine factory
- connection string from config

### 4.2 — Schema creation helper

File: `gateway/infrastructure/persistence/postgres/schema.py`

- `CREATE EXTENSION IF NOT EXISTS citext`
- DDL for `api_consumers`, `fints_institutes`, `product_registrations`
- used in tests to create/drop the schema; not the production migration mechanism

### 4.3 — `PostgresApiConsumerRepository`

File: `gateway/infrastructure/persistence/postgres/consumer_repository.py`

Implements `ApiConsumerRepository`. No ORM — use raw SQL with `asyncpg` or SQLAlchemy core. Maps rows to `ApiConsumer` aggregates.

Tests: save → get, get missing returns None, list active returns only active.

### 4.4 — `PostgresFinTSInstituteRepository`

File: `gateway/infrastructure/persistence/postgres/institute_repository.py`

Implements `FinTSInstituteRepository`. `replace_catalog` should run in one transaction: delete all, insert new batch.

Tests: replace → list, get by BLZ, get unknown BLZ returns None.

### 4.5 — `PostgresFinTSProductRegistrationRepository`

File: `gateway/infrastructure/persistence/postgres/product_registration_repository.py`

Implements `FinTSProductRegistrationRepository`. There is only ever one row; `get_current()` is a simple `SELECT ... LIMIT 1`.

Tests: save → get, no row returns None.

### 4.6 — CSV ingestion helper

File: `gateway/infrastructure/persistence/csv/institute_csv_reader.py`

- Parses `fints_institute.csv`
- Normalizes each row into a `FinTSInstitute` domain object
- Returns `list[FinTSInstitute]` (unresolved duplicates; `InstituteSelectionPolicy` is applied by the use case)

Tests: `tests/apps/gateway/infrastructure/test_csv_reader.py`

- parse a small fixture CSV with known content
- duplicate BLZ rows appear separately in output (resolution is the use case's job)

---

## Phase 5 — Infrastructure: in-memory caches

Work in `gateway/infrastructure/cache/memory/`.

### 5.1 — `InMemoryApiConsumerCache`

File: `consumer_cache.py`

- `list_active() -> list[ApiConsumer]`
- `load(consumers: list[ApiConsumer]) -> None`
- `evict(consumer_id: ConsumerId) -> None`
- `reload_one(consumer: ApiConsumer) -> None`

Thread-safe with `asyncio.Lock` (or a read-write lock pattern if contention warrants it).

### 5.2 — `InMemoryFinTSInstituteCache`

File: `institute_cache.py`

- `get_by_blz(blz: BankLeitzahl) -> FinTSInstitute | None`
- `load(institutes: list[FinTSInstitute]) -> None` — rebuilds the entire index

### 5.3 — `InMemoryProductRegistrationCache`

File: `product_registration_cache.py`

- `get_current() -> FinTSProductRegistration | None`
- `set_current(registration: FinTSProductRegistration) -> None`

### 5.4 — `InMemoryOperationSessionStore`

File: `operation_session_store.py`

Implements `OperationSessionStore`.

- backed by a `dict[str, PendingOperationSession]`
- `expire_stale(now)` iterates and removes expired entries; returns count removed
- `create` enforces the maximum session cap; raises `InternalError` when full
- `asyncio.Lock` on all mutations

### 5.5 — PostgreSQL NOTIFY listener

File: `gateway/infrastructure/cache/memory/notify_listener.py`

- opens a dedicated `asyncpg` connection (not from the pool; NOTIFY requires persistent listen state)
- registers `LISTEN gw.consumer_updated`, `LISTEN gw.catalog_replaced`, `LISTEN gw.product_registration_updated`
- on notification: routes to the correct cache update function
- recovers from dropped connections with exponential backoff

Tests: `tests/apps/gateway/infrastructure/test_notify_listener.py` (integration, skippable).

---

## Phase 6 — Infrastructure: banking connector (anti-corruption layer)

Work in `gateway/infrastructure/banking/geldstrom/`.

### 6.1 — `GeldstromBankingConnector`

File: `connector.py`

Implements `BankingConnector`.

Each method:

1. maps gateway value objects → Geldstrom client inputs
2. calls the appropriate Geldstrom client method
3. catches all Geldstrom exceptions and maps them using the exception mapping table from `api_architecture.md`
4. maps Geldstrom results → gateway result dataclasses
5. for decoupled flows: serialises the Geldstrom session state into `bytes` that `resume_operation` can deserialize

`resume_operation`:

1. deserialises `session_state` back to a Geldstrom session object
2. polls the bank for decoupled confirmation status
3. returns `ResumeResult` with updated status and final payload if completed

### 6.2 — Protocol dispatcher

File: `gateway/infrastructure/banking/protocols/dispatcher.py`

- `BankingConnectorDispatcher.get(protocol: BankProtocol) -> BankingConnector`
- raises `UnsupportedProtocolError` for unknown protocols
- `GeldstromBankingConnector` is registered for `BankProtocol.FINTS`

Tests: `tests/apps/gateway/infrastructure/test_connector.py`

- use a real Geldstrom fake or a mock for structured unit tests
- integration tests against a real bank are in `tests/apps/gateway/integration/` (skippable)

---

## Phase 7 — Backend bootstrap and composition root

Work in `gateway/bootstrap/`.

### 7.1 — Configuration

File: `config.py`

`Settings` (Pydantic `BaseSettings`):

- `database_url: SecretStr`
- `product_master_key: SecretStr`
- `argon2_time_cost: int = 2`
- `argon2_memory_cost: int = 65536`
- `argon2_parallelism: int = 2`
- `operation_session_ttl_seconds: int = 120`
- `operation_session_max_count: int = 10000`
- `rate_limit_requests_per_minute: int = 60`
- `notify_reconnect_backoff_seconds: float = 1.0`

### 7.2 — Composition root

File: `container.py`

Provides factory functions and singletons:

```python
def get_settings() -> Settings: ...
def get_db_engine() -> AsyncEngine: ...
def get_consumer_repository(engine) -> ApiConsumerRepository: ...
def get_institute_repository(engine) -> FinTSInstituteRepository: ...
def get_product_repository(engine) -> FinTSProductRegistrationRepository: ...
def get_api_key_service(settings) -> ApiKeyService: ...
def get_product_key_service(settings) -> ProductKeyService: ...
def get_product_key_provider(...) -> CurrentProductKeyProvider: ...
def get_consumer_cache() -> InMemoryApiConsumerCache: ...     # singleton
def get_institute_cache() -> InMemoryFinTSInstituteCache: ... # singleton
def get_product_cache() -> InMemoryProductRegistrationCache: # singleton
def get_session_store(settings) -> InMemoryOperationSessionStore: ... # singleton
def get_connector_dispatcher() -> BankingConnectorDispatcher: ...
def get_list_accounts_use_case(...) -> ListAccounts: ...
# ... one factory per use case
```

### 7.3 — Lifecycle

File: `lifecycle.py`

`startup(container)`:

1. initialize engine
2. warm consumer cache
3. warm institute cache
4. warm product registration cache and hydrate the internal current-product-key provider from it
5. initialize empty session store
6. start NOTIFY listener task
7. start `ResumePendingOperations` periodic task (asyncio)
8. start expired-session sweeper periodic task (asyncio)

`shutdown(container)`:

1. cancel background tasks
2. close NOTIFY listener connection
3. close DB engine pool

---

## Phase 8 — `gateway` presentation layer

Work in `gateway/`.

### 8.1 — FastAPI app + lifespan

File: `gateway/presentation/http/api.py`

- create FastAPI app
- attach lifespan context manager that calls `startup` / `shutdown` from `gateway.bootstrap.lifecycle`
- register routers

### 8.2 — Middleware

Files: `gateway/presentation/http/middleware/`

- `request_id.py` — reads `X-Request-Id` header; generates one if absent; attaches to response
- `no_body_log.py` — prevent body contents from being logged (override access log or use structlog filter)
- `cache_control.py` — set `Cache-Control: no-store` on all non-health responses

Do not implement consumer-specific rate limiting as pre-auth middleware.

FastAPI middleware runs before route dependencies, so authenticated identity is not available there.

Implement consumer-specific rate limiting as an authenticated dependency or route guard instead.

### 8.3 — Pydantic schemas

Files: `gateway/presentation/http/schemas/`

One file per domain area:

- `health.py` — `LiveResponse`, `ReadyResponse`, `NotReadyResponse`
- `bank_access.py` — `BankAccessRequestSchema`, `TransactionHistoryRequestSchema`
- `accounts.py` — `AccountSchema`, `AccountsResponse`
- `transactions.py` — `TransactionSchema`, `TransactionsResponse`
- `tan_methods.py` — `TanMethodSchema`, `TanMethodsResponse`
- `operations.py` — `PendingOperationResponse`, `CompletedOperationResponse`, `FailedOperationResponse`, `ExpiredOperationResponse`
- `errors.py` — `ErrorDetail`, `ErrorResponse`

All secret-bearing request fields use `pydantic.SecretStr`. Request schemas have `model_config = ConfigDict(extra="forbid")`.

### 8.4 — FastAPI dependencies

File: `gateway/presentation/http/dependencies.py`

- `get_authenticated_consumer(x_api_key: str = Header(...)) -> AuthenticatedConsumer`
  - calls `AuthenticateConsumer` use case
  - maps `UnauthorizedError` → `401`, `ForbiddenError` → `403`
- `enforce_consumer_rate_limit(authenticated: AuthenticatedConsumer = Depends(get_authenticated_consumer)) -> None`
  - applies the fixed-window consumer rate limit after authentication has resolved identity
  - maps limit exhaustion to `429` and sets `Retry-After`
- `get_list_accounts_use_case() -> ListAccounts` — thin wrapper around container factory
- one dependency per use case

### 8.5 — Routers

Files: `gateway/presentation/http/routers/`

- `health.py` — `GET /health/live`, `GET /health/ready`
- `accounts.py` — `POST /v1/banking/accounts`
- `transactions.py` — `POST /v1/banking/transactions`
- `tan_methods.py` — `POST /v1/banking/tan-methods`
- `operations.py` — `GET /v1/banking/operations/{operation_id}`

Each router function:

1. accepts request schema
2. maps schema → domain value objects
3. runs authenticated rate-limit dependency
4. calls use case
5. maps use case result → response schema
6. returns appropriate HTTP status code (200 or 202)

### 8.6 — Exception handlers

File: `gateway/presentation/http/middleware/exception_handlers.py`

- catch all `ApplicationError` subclasses → `ErrorResponse` with correct HTTP status
- catch `ValidationError` (Pydantic) → `400`
- catch unhandled exceptions → `500` with a generic `internal_error` message (no stack trace in response)
- all handlers attach `request_id` from request state

### 8.7 — `gateway` composition root

File: `gateway/bootstrap/container.py`

- exposes shared service factories and singletons to the HTTP presentation layer
- provides FastAPI-specific wiring (settings override for CORS if needed, etc.)

### 8.8 — Entry point

File: `gateway/main.py`

```python
import uvicorn
from gateway.presentation.http.api import app

def main() -> None:
  uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
  main()
```

Add to `pyproject.toml`:

```toml
[project.scripts]
gateway = "gateway.main:main"
```

Tests: `tests/apps/gateway/`

- use `httpx.AsyncClient(app=app, base_url="http://test")`
- test each endpoint with valid and invalid inputs
- assert `401` when no API key
- assert `202` shape when fake connector returns decoupled
- assert `200` shape when fake connector returns completed
- assert body never appears in log output (security regression)

---

## Phase 9 — `gateway_admin_cli` presentation layer

Work in `gateway_admin_cli/`.

### 9.1 — Typer app

File: `gateway_admin_cli/presentation/cli/main.py`

- create `typer.Typer` app
- register sub-apps: `institutes`, `consumers`, `product_key`, `health`

### 9.2 — `institutes` commands

File: `presentation/cli/commands/institutes.py`

- `institutes sync [--csv-path PATH]` — calls `SyncInstituteCatalog`; prints count of loaded institutes
- `institutes inspect [--blz BLZ]` — calls `InspectBackendState` and formats institute cache info; supports `--json`

### 9.3 — `consumers` commands

File: `presentation/cli/commands/consumers.py`

- `consumers create --email EMAIL` — calls `CreateApiConsumer`; prints raw API key once with a warning to store it
- `consumers update --id ID --email EMAIL` — calls `UpdateApiConsumer`; updates mutable consumer metadata
- `consumers disable --id ID` — calls `DisableApiConsumer`; confirms unless `--yes`
- `consumers delete --id ID` — calls `DeleteApiConsumer`; confirms unless `--yes`
- `consumers rotate-key --id ID` — calls `RotateApiConsumerKey`; prints new key once
- `consumers list` — calls `ListApiConsumers`; lists consumers (id, email, status, created_at) in table format; supports `--json`

### 9.4 — `product-key` commands

File: `presentation/cli/commands/product_key.py`

- `product-key update` — prompts for new key with `typer.prompt(hide_input=True)`; calls `UpdateProductRegistration`

### 9.5 — `health` commands

File: `presentation/cli/commands/health.py`

- `health inspect` — calls `InspectBackendState`; prints table of check name → status; supports `--json`

### 9.6 — Formatters

File: `presentation/cli/formatters/`

- `table.py` — wraps `rich.table.Table` for consistent column formatting
- `json_output.py` — JSON serialiser that converts domain objects to dicts safely

### 9.7 — `gateway_admin_cli` composition root

File: `gateway_admin_cli/bootstrap/container.py`

- manual factory: `build_sync_catalog() -> SyncInstituteCatalog`, `build_update_consumer() -> UpdateApiConsumer`, `build_list_consumers() -> ListApiConsumers`, etc.
- initialises DB engine, repositories, caches, crypto services
- CLI commands call these at the start of each command function

### 9.8 — Entry point

File: `gateway_admin_cli/main.py`

```python
from gateway_admin_cli.presentation.cli.main import app

def main() -> None:
  app()

if __name__ == "__main__":
  main()
```

Add to `pyproject.toml`:

```toml
[project.scripts]
gateway-admin = "gateway_admin_cli.main:main"
```

---

## Phase 10 — Observability and hardening

### 10.1 — Structured logging

File: `gateway/bootstrap/logging.py`

- configure `structlog` (or stdlib `logging` with JSON formatter)
- allowlist-based field filter: only `request_id`, `route`, `method`, `status`, `duration_ms`, `consumer_id` pass through
- no request body, no secret fields

### 10.2 — Prometheus metrics (optional for v1)

If desired, add `prometheus-fastapi-instrumentator` to `gateway` and expose `/metrics`.

Safe labels only: route, method, status.

### 10.3 — Security regression test suite

File: `tests/apps/gateway/security/test_secret_safety.py`

Assertions:

- calling `ListAccounts` with a real (fake) connector does not produce any log records containing the bank password
- serialising an `ApplicationError` does not include `SecretStr` contents
- `ApiConsumer` serialised to dict does not include a raw API key (only hash)
- `FinTSProductRegistration` serialised to dict does not include a plaintext key

---

## Sequence summary

```text
Phase 0:  workspace scaffolding        (no tests yet)
Phase 1:  domain layer                 (pure unit tests)
Phase 2:  application use cases        (unit tests with fakes)
Phase 3:  crypto infrastructure        (unit tests)
Phase 4:  postgres persistence         (integration tests, skippable)
Phase 5:  in-memory caches             (unit tests)
Phase 6:  banking connector / ACL      (unit + skippable integration)
Phase 7:  backend bootstrap            (tested implicitly by later phases)
Phase 8:  gateway HTTP layer       (httpx-based API tests)
Phase 9:  gateway_admin_cli layer      (typer CliRunner tests)
Phase 10: observability and hardening  (security regression tests)
```

Each phase can be code-reviewed independently. Phases 1–3 produce no runtime artifact but provide the stable foundation everything else builds on.

---

## What is explicitly out of scope for v1

- database migrations (Alembic or similar) — schema is created by the test helper for now; a migrator is chosen before the first real deployment
- Redis for shared cache or rate limit state
- multi-tenant product registrations
- bank response caching
- pagination on transactions
- long-lived bank sessions across requests
- background transaction persistence
