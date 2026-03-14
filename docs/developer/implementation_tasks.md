# Gateway Implementation Tasks

This document turns the gateway architecture and implementation plan into an execution backlog.

It is intended for day-to-day delivery work.

Use it together with:

- `docs/developer/api_architecture.md`
- `docs/developer/implementation_plan.md`

The plan explains **what** should be built and in which phase.
This task document explains **how to execute it in concrete work items**.

---

## Delivery Rules

These rules apply to every task:

1. Finish one vertical dependency slice at a time.
2. Keep domain and application layers free of infrastructure imports.
3. Write tests together with the implementation, not afterwards.
4. Do not implement future protocols, persistence of bank data, or bank response caching in v1.
5. Every task must end in a runnable or testable state.

Recommended workflow for each task:

1. create scaffold
2. write or update tests
3. implement behavior
4. run the smallest relevant test subset
5. review naming and boundaries

---

## Task Structure

Each task contains:

- `Goal`: what is delivered
- `Files`: files or modules to create or edit
- `Scaffolding`: classes, functions, and interfaces that should exist after the task
- `Tests`: tests to add or update
- `Done when`: concrete acceptance criteria
- `Depends on`: earlier tasks that should be complete first

---

## Milestone A — Monorepo Scaffolding

### Task A1 — Create workspace app packages

Status:

- completed on 2026-03-07

Goal:

- establish the gateway service app and admin CLI package roots

Files:

- `apps/gateway/pyproject.toml`
- `apps/gateway/README.md`
- `apps/gateway/gateway/__init__.py`
- `apps/gateway_admin_cli/pyproject.toml`
- `apps/gateway_admin_cli/README.md`
- `apps/gateway_admin_cli/gateway_admin_cli/__init__.py`
- root `pyproject.toml`

Scaffolding:

- package names:
  - `gateway`
  - `gateway-admin-cli`
- root uv workspace sources updated to include both workspace apps
- Ruff sources include `apps`

Tests:

- no unit tests yet
- smoke command: `uv run python -c "import gateway, gateway_admin_cli"`

Done when:

- both packages import successfully
- `uv lock` succeeds
- root lint/test config still resolves

Depends on:

- none

### Task A2 — Create test package roots

Status:

- completed on 2026-03-07

Goal:

- establish the package-specific test layout

Files:

- `tests/apps/gateway/__init__.py`
- `tests/apps/gateway_admin_cli/__init__.py`
- `tests/apps/gateway/conftest.py`
- `tests/apps/gateway_admin_cli/conftest.py`

Scaffolding:

- empty package roots
- shared fixtures placeholders per package

Tests:

- no assertions needed yet

Done when:

- pytest discovers the new roots without import errors

Depends on:

- `A1`

---

## Milestone B — Pure Domain Core

### Task B1 — Shared domain primitives

Status:

- completed on 2026-03-07

Goal:

- create the shared domain foundation used by all bounded contexts

Files:

- `apps/gateway/gateway/domain/shared/__init__.py`
- `apps/gateway/gateway/domain/shared/errors.py`
- `apps/gateway/gateway/domain/shared/ids.py`
- `apps/gateway/gateway/domain/shared/protocols.py`

Scaffolding:

```python
class DomainError(Exception): ...

@dataclass(frozen=True)
class EntityId: ...

class BankProtocol(str, Enum):
    FINTS = "fints"
```

Tests:

- `tests/apps/gateway/domain/test_shared.py`
- validate UUID wrapping behavior
- validate `BankProtocol.FINTS`

Done when:

- the shared domain package is importable
- tests pass with no infrastructure imports

Depends on:

- `A1`, `A2`

### Task B2 — Consumer access domain

Status:

- completed on 2026-03-07

Goal:

- model API consumers and hash verification contracts

Files:

- `apps/gateway/gateway/domain/consumer_access/__init__.py`
- `apps/gateway/gateway/domain/consumer_access/model.py`
- `apps/gateway/gateway/domain/consumer_access/value_objects.py`
- `apps/gateway/gateway/domain/consumer_access/services.py`
- `apps/gateway/gateway/domain/consumer_access/repositories.py`

Scaffolding:

```python
class ConsumerStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    DELETED = "deleted"

@dataclass(frozen=True)
class ConsumerId(EntityId): ...

@dataclass(frozen=True)
class EmailAddress: ...

@dataclass(frozen=True)
class ApiKeyHash: ...

@dataclass
class ApiConsumer: ...

class ApiKeyVerifier(Protocol):
    def verify(self, presented_key: str, stored_hash: ApiKeyHash) -> bool: ...

class ApiConsumerRepository(Protocol):
    async def get_by_id(self, consumer_id: ConsumerId) -> ApiConsumer | None: ...
    async def get_by_email(self, email: EmailAddress) -> ApiConsumer | None: ...
    async def list_all_active(self) -> list[ApiConsumer]: ...
    async def save(self, consumer: ApiConsumer) -> None: ...
```

Tests:

- `tests/apps/gateway/domain/test_consumer_access.py`
- valid and invalid email construction
- active consumer must have hash
- deleted consumer cannot be directly reactivated

Done when:

- domain invariants are enforced
- no hashing implementation leaks into domain

Depends on:

- `B1`

### Task B3 — Institution catalog domain

Status:

- completed on 2026-03-07

Goal:

- model canonical institute data and duplicate resolution rules

Files:

- `apps/gateway/gateway/domain/institution_catalog/__init__.py`
- `apps/gateway/gateway/domain/institution_catalog/model.py`
- `apps/gateway/gateway/domain/institution_catalog/value_objects.py`
- `apps/gateway/gateway/domain/institution_catalog/services.py`
- `apps/gateway/gateway/domain/institution_catalog/repositories.py`

Scaffolding:

```python
@dataclass(frozen=True)
class BankLeitzahl: ...

@dataclass(frozen=True)
class Bic: ...

@dataclass(frozen=True)
class InstituteEndpoint: ...

@dataclass
class FinTSInstitute:
    def is_pin_tan_capable(self) -> bool: ...

class InstituteSelectionPolicy:
    @staticmethod
    def select(candidates: list[FinTSInstitute]) -> FinTSInstitute: ...

class FinTSInstituteRepository(Protocol): ...
```

Tests:

- `tests/apps/gateway/domain/test_institution_catalog.py`
- BLZ validation
- BIC validation
- duplicate resolution across all tie-break stages

Done when:

- deterministic canonical selection is tested

Depends on:

- `B1`

### Task B4 — Product registration domain

Status:

- completed on 2026-03-07

Goal:

- model encrypted product registration without plaintext exposure

Files:

- `apps/gateway/gateway/domain/product_registration/__init__.py`
- `apps/gateway/gateway/domain/product_registration/model.py`
- `apps/gateway/gateway/domain/product_registration/value_objects.py`
- `apps/gateway/gateway/domain/product_registration/repositories.py`

Scaffolding:

```python
@dataclass(frozen=True)
class EncryptedProductKey: ...

@dataclass(frozen=True)
class ProductVersion: ...

@dataclass(frozen=True)
class KeyVersion: ...

@dataclass
class FinTSProductRegistration: ...

class FinTSProductRegistrationRepository(Protocol): ...
```

Tests:

- `tests/apps/gateway/domain/test_product_registration.py`
- construct aggregate
- ensure no plaintext accessor exists

Done when:

- only encrypted product key material is represented

Depends on:

- `B1`

### Task B5 — Banking gateway domain

Status:

- completed on 2026-03-07

Goal:

- model transient bank-facing value objects, operation states, connector port, and operation session state

Files:

- `apps/gateway/gateway/domain/banking_gateway/__init__.py`
- `apps/gateway/gateway/domain/banking_gateway/value_objects.py`
- `apps/gateway/gateway/domain/banking_gateway/operations.py`
- `apps/gateway/gateway/domain/banking_gateway/services.py`
- `apps/gateway/gateway/domain/banking_gateway/ports.py`

Scaffolding:

```python
@dataclass(frozen=True)
class PresentedBankUserId: ...

@dataclass(frozen=True)
class PresentedBankPassword: ...

@dataclass(frozen=True)
class RequestedIban: ...

@dataclass(frozen=True)
class AuthenticatedConsumer: ...

@dataclass(frozen=True)
class PresentedBankCredentials: ...

class OperationStatus(str, Enum):
    PENDING_CONFIRMATION = "pending_confirmation"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"

@dataclass
class PendingOperationSession: ...

class BankRequestSanitizationPolicy:
    @staticmethod
    def sanitize(credentials: PresentedBankCredentials) -> None: ...

class AccountsResult: ...
class TransactionsResult: ...
class TanMethodsResult: ...
class ResumeResult: ...

class BankingConnector(Protocol): ...
class OperationSessionStore(Protocol): ...
```

Tests:

- `tests/apps/gateway/domain/test_banking_gateway.py`
- empty secret validation
- IBAN validation
- operation session model construction

Done when:

- transient banking types are defined with no infrastructure dependencies

Depends on:

- `B1`, `B2`

---

## Milestone C — Application Layer with Fakes

### Task C1 — Application error model

Status:

- completed on 2026-03-07

Goal:

- create the application error vocabulary used by HTTP and CLI presentation layers

Files:

- `apps/gateway/gateway/application/common/__init__.py`
- `apps/gateway/gateway/application/common/errors.py`
- `apps/gateway/gateway/application/common/time.py`

Scaffolding:

```python
class GatewayErrorCode(str, Enum): ...
class ApplicationError(Exception): ...
class UnauthorizedError(ApplicationError): ...
class ForbiddenError(ApplicationError): ...
class InstitutionNotFoundError(ApplicationError): ...
class OperationNotFoundError(ApplicationError): ...
class OperationExpiredError(ApplicationError): ...
class UnsupportedProtocolError(ApplicationError): ...
class BankUpstreamUnavailableError(ApplicationError): ...
class InternalError(ApplicationError): ...

class IdProvider(Protocol):
    def new_operation_id(self) -> str: ...
    def now(self) -> datetime: ...
```

Tests:

- `tests/apps/gateway/application/test_errors.py`
- error codes map correctly

Done when:

- all later use cases can raise stable application errors

Depends on:

- `B2`, `B3`, `B4`, `B5`

### Task C2 — Fake ports for application tests

Status:

- completed on 2026-03-07

Goal:

- provide in-memory fake implementations for application-level testing

Files:

- `tests/apps/gateway/fakes/fake_consumer_cache.py`
- `tests/apps/gateway/fakes/fake_institute_cache.py`
- `tests/apps/gateway/fakes/fake_product_key_provider.py`
- `tests/apps/gateway/fakes/fake_operation_session_store.py`
- `tests/apps/gateway/fakes/fake_banking_connector.py`
- `tests/apps/gateway/fakes/fake_id_provider.py`

Scaffolding:

- fake caches and connector with deterministic behavior
- fake connector should support:
  - completed account result
  - completed transactions result
  - completed tan-methods result
  - decoupled-required result
  - resume-to-completed transition
  - resume-to-failed transition

Tests:

- smoke tests inside application suite as these fakes are used

Done when:

- all application use case tests can run without PostgreSQL or Geldstrom

Depends on:

- `C1`

### Task C3 — `AuthenticateConsumer`

Status:

- completed on 2026-03-07

Goal:

- authenticate by scanning the in-memory active-consumer cache and verifying Argon2id hashes

Files:

- `apps/gateway/gateway/application/consumer_access/authenticate_consumer.py`

Scaffolding:

```python
class ConsumerCachePort(Protocol):
    async def list_active(self) -> list[ApiConsumer]: ...

class AuthenticateConsumer:
    async def __call__(self, presented_key: str) -> AuthenticatedConsumer: ...
```

Implementation notes:

- iterate over `list_active()`
- call `ApiKeyVerifier.verify(...)` until one match is found
- raise `UnauthorizedError` when none match
- raise `ForbiddenError` when matching consumer is disabled

Tests:

- `tests/apps/gateway/application/test_authenticate_consumer.py`
- valid consumer found
- invalid key rejected
- disabled consumer rejected
- multiple active consumers with only one matching hash

Done when:

- behavior matches the chosen v1 authentication strategy

Depends on:

- `C1`, `C2`

### Task C4 — Internal product key provider abstraction

Status:

- completed on 2026-03-07

Goal:

- keep the shared FinTS product key internal to the backend and out of public use case signatures

Files:

- `apps/gateway/gateway/application/product_registration/current_product_key.py`

Scaffolding:

```python
class CurrentProductKeyProvider(Protocol):
    async def require_current(self) -> str: ...
```

Implementation note:

- this is an internal backend abstraction
- it is not exposed through HTTP or CLI outputs
- if no key is loaded, it raises `InternalError`

Tests:

- `tests/apps/gateway/application/test_current_product_key_provider.py`
- returns key when loaded
- raises when no current key is available

Done when:

- banking use cases can depend on this provider instead of receiving a plaintext key as a parameter

Depends on:

- `C1`

### Task C5 — `ListAccounts`

Status:

- completed on 2026-03-07

Goal:

- orchestrate account retrieval through the gateway use case

Files:

- `apps/gateway/gateway/application/banking_gateway/list_accounts.py`

Scaffolding:

```python
class ListAccounts:
    async def __call__(self, request: ListAccountsCommand, presented_api_key: str) -> ListAccountsResultEnvelope: ...
```

Tests:

- `tests/apps/gateway/application/test_list_accounts.py`
- completed response path
- decoupled response path creates session
- unknown BLZ -> `InstitutionNotFoundError`
- missing product key -> `InternalError`

Done when:

- completed and pending flows are covered

Depends on:

- `C3`, `C4`

### Task C6 — `FetchHistoricalTransactions`

Status:

- completed on 2026-03-07

Goal:

- orchestrate transaction retrieval with default date-window behavior

Files:

- `apps/gateway/gateway/application/banking_gateway/fetch_transactions.py`

Scaffolding:

```python
class FetchHistoricalTransactions:
    async def __call__(self, request: FetchTransactionsCommand, presented_api_key: str) -> TransactionsResultEnvelope: ...
```

Tests:

- `tests/apps/gateway/application/test_fetch_transactions.py`
- explicit date range
- default range = today back to 90 days
- pending decoupled path

Done when:

- date window logic and decoupled flow are covered

Depends on:

- `C3`, `C4`

### Task C7 — `GetAllowedTanMethods`

Status:

- completed on 2026-03-07

Goal:

- expose only decoupled-compatible TAN methods

Files:

- `apps/gateway/gateway/application/banking_gateway/get_tan_methods.py`

Scaffolding:

```python
class GetAllowedTanMethods:
    async def __call__(self, request: TanMethodsCommand, presented_api_key: str) -> TanMethodsResultEnvelope: ...
```

Tests:

- `tests/apps/gateway/application/test_get_tan_methods.py`
- mixed methods from connector are filtered to decoupled only
- pending path creates session when required

Done when:

- non-decoupled methods never escape the use case

Depends on:

- `C3`, `C4`

### Task C8 — `GetOperationStatus`

Status:

- completed on 2026-03-07

Goal:

- expose pending/completed/failed/expired state transitions safely per consumer

Files:

- `apps/gateway/gateway/application/banking_gateway/get_operation_status.py`

Scaffolding:

```python
class GetOperationStatus:
    async def __call__(self, operation_id: str, presented_api_key: str) -> OperationStatusEnvelope: ...
```

Tests:

- `tests/apps/gateway/application/test_get_operation_status.py`
- wrong consumer cannot access another consumer's operation
- completed result is returned and then cleaned up when appropriate
- missing operation -> `OperationNotFoundError`

Done when:

- per-consumer isolation is enforced

Depends on:

- `C3`, `C2`

### Task C9 — `ResumePendingOperations`

Status:

- completed on 2026-03-07

Goal:

- poll decoupled sessions and transition them forward

Files:

- `apps/gateway/gateway/application/operation_sessions/resume_pending_operations.py`

Scaffolding:

```python
class ResumePendingOperations:
    async def __call__(self) -> ResumeSummary: ...
```

Tests:

- `tests/apps/gateway/application/test_resume_pending_operations.py`
- pending -> completed
- pending -> failed
- pending -> expired

Done when:

- periodic background behavior can be exercised with fakes

Depends on:

- `C4`, `C2`

### Task C10 — `EvaluateHealth`

Status:

- completed on 2026-03-12

Goal:

- centralize liveness and readiness evaluation

Files:

- `apps/gateway/gateway/application/health/evaluate_health.py`

Scaffolding:

```python
class EvaluateHealth:
    async def live(self) -> dict[str, str]: ...
    async def ready(self) -> dict[str, Any]: ...
```

Tests:

- `tests/apps/gateway/application/test_evaluate_health.py`
- all checks healthy
- one check failed produces `not_ready`

Done when:

- readiness output matches the API contract

Depends on:

- `C1`

### Task C11 — Administration use cases

Status:

- completed on 2026-03-12

Goal:

- implement the admin CLI-backed application services

Files:

- `apps/gateway/gateway/application/administration/sync_institute_catalog.py`
- `apps/gateway/gateway/application/administration/create_api_consumer.py`
- `apps/gateway/gateway/application/administration/update_api_consumer.py`
- `apps/gateway/gateway/application/administration/list_api_consumers.py`
- `apps/gateway/gateway/application/administration/rotate_api_consumer_key.py`
- `apps/gateway/gateway/application/administration/disable_api_consumer.py`
- `apps/gateway/gateway/application/administration/delete_api_consumer.py`
- `apps/gateway/gateway/application/administration/update_product_registration.py`
- `apps/gateway/gateway/application/administration/inspect_backend_state.py`

Scaffolding:

- one class per use case
- each class exposes `async def __call__(...)`
- `ListApiConsumers` returns summaries only, never secrets
- `UpdateApiConsumer` only updates non-secret mutable fields

Tests:

- `tests/apps/gateway/application/test_administration.py`
- create returns raw key once
- list returns summaries without secrets
- update changes email
- rotate returns a new raw key once
- update product registration refreshes internal key provider and cache

Done when:

- all admin flows required by the CLI are backed by real use cases

Depends on:

- `C1`, `C2`, `C4`

---

## Milestone D — Crypto and Persistence Infrastructure

### Task D1 — API key service

Status:

- completed on 2026-03-12

Goal:

- generate and verify API keys using Argon2id

Files:

- `apps/gateway/gateway/infrastructure/crypto/api_key_service.py`

Scaffolding:

```python
class Argon2ApiKeyService:
    def generate(self) -> str: ...
    def hash(self, raw_key: str) -> ApiKeyHash: ...
    def verify(self, raw_key: str, stored_hash: ApiKeyHash) -> bool: ...
```

Tests:

- `tests/apps/gateway/infrastructure/test_api_key_service.py`
- generate produces unique values
- hash/verify round trip
- wrong key fails verification

Done when:

- service implements the `ApiKeyVerifier` contract

Depends on:

- `B2`

### Task D2 — Product key crypto service

Status:

- completed on 2026-03-12

Goal:

- encrypt and decrypt shared FinTS product key material internally

Files:

- `apps/gateway/gateway/infrastructure/crypto/product_key_service.py`

Scaffolding:

```python
class ProductKeyService:
    def encrypt(self, plaintext: str) -> EncryptedProductKey: ...
    def decrypt(self, encrypted: EncryptedProductKey) -> str: ...
```

Tests:

- `tests/apps/gateway/infrastructure/test_product_key_service.py`
- encrypt/decrypt round trip
- wrong master key fails

Done when:

- product key material can be stored only in encrypted form

Depends on:

- `B4`

### Task D3 — PostgreSQL connection and test schema helper

Status:

- completed on 2026-03-12

Goal:

- provide a reusable PostgreSQL test harness and schema bootstrap

Files:

- `apps/gateway/gateway/infrastructure/persistence/postgres/connection.py`
- `apps/gateway/gateway/infrastructure/persistence/postgres/schema.py`
- `tests/apps/gateway/conftest.py`

Scaffolding:

```python
def build_engine(database_url: str) -> AsyncEngine: ...
async def create_test_schema(engine: AsyncEngine) -> None: ...
async def drop_test_schema(engine: AsyncEngine) -> None: ...
```

Tests:

- smoke integration test that creates and tears down schema

Done when:

- integration repository tests can reuse the same setup

Depends on:

- `A2`

### Task D4 — Consumer repository

Status:

- completed on 2026-03-12

Goal:

- persist and load API consumers from PostgreSQL

Files:

- `apps/gateway/gateway/infrastructure/persistence/postgres/consumer_repository.py`

Scaffolding:

```python
class PostgresApiConsumerRepository(ApiConsumerRepository): ...
```

Tests:

- `tests/apps/gateway/infrastructure/test_consumer_repository.py`
- save/get
- list active
- update existing consumer

Done when:

- repository round-trips `ApiConsumer`

Depends on:

- `D3`, `B2`

### Task D5 — Institution repository

Status:

- completed on 2026-03-12

Goal:

- persist canonical institute catalog and replace it transactionally

Files:

- `apps/gateway/gateway/infrastructure/persistence/postgres/institute_repository.py`

Scaffolding:

```python
class PostgresFinTSInstituteRepository(FinTSInstituteRepository): ...
```

Tests:

- `tests/apps/gateway/infrastructure/test_institute_repository.py`
- replace catalog
- get by BLZ
- unknown BLZ returns `None`

Done when:

- canonical catalog storage is transactionally replaceable

Depends on:

- `D3`, `B3`

### Task D6 — Product registration repository

Status:

- completed on 2026-03-12

Goal:

- persist encrypted product registration data

Files:

- `apps/gateway/gateway/infrastructure/persistence/postgres/product_registration_repository.py`

Scaffolding:

```python
class PostgresFinTSProductRegistrationRepository(FinTSProductRegistrationRepository): ...
```

Tests:

- `tests/apps/gateway/infrastructure/test_product_registration_repository.py`
- save current
- get current
- update current

Done when:

- product registration storage round-trips encrypted values only

Depends on:

- `D3`, `B4`

### Task D7 — CSV reader

Status:

- completed on 2026-03-12

Goal:

- parse the institute CSV into domain objects

Files:

- `apps/gateway/gateway/infrastructure/persistence/csv/institute_csv_reader.py`
- `tests/apps/gateway/fixtures/institutes/sample_fints_institute.csv`

Scaffolding:

```python
class InstituteCsvReader:
    def read(self, path: Path) -> list[FinTSInstitute]: ...
```

Tests:

- `tests/apps/gateway/infrastructure/test_csv_reader.py`
- fixture parsing
- duplicate BLZ rows preserved in raw output

Done when:

- CSV parsing is separated from canonical selection

Depends on:

- `B3`

---

## Milestone E — Runtime Caches and Background State

### Task E1 — API consumer cache

Status:

- completed on 2026-03-12

Goal:

- maintain the in-memory active-consumer read model used by authentication

Files:

- `apps/gateway/gateway/infrastructure/cache/memory/consumer_cache.py`

Scaffolding:

```python
class InMemoryApiConsumerCache:
    async def list_active(self) -> list[ApiConsumer]: ...
    async def load(self, consumers: list[ApiConsumer]) -> None: ...
    async def evict(self, consumer_id: ConsumerId) -> None: ...
    async def reload_one(self, consumer: ApiConsumer) -> None: ...
```

Tests:

- `tests/apps/gateway/infrastructure/test_consumer_cache.py`
- load and list
- evict
- reload one

Done when:

- authentication can use the cache without any DB call

Depends on:

- `B2`

### Task E2 — Institute and product registration caches

Status:

- completed on 2026-03-12

Goal:

- maintain in-memory read models for canonical institutes and encrypted product registration data

Files:

- `apps/gateway/gateway/infrastructure/cache/memory/institute_cache.py`
- `apps/gateway/gateway/infrastructure/cache/memory/product_registration_cache.py`
- `apps/gateway/gateway/infrastructure/cache/memory/current_product_key_provider.py`

Scaffolding:

```python
class InMemoryFinTSInstituteCache: ...
class InMemoryProductRegistrationCache: ...
class InMemoryCurrentProductKeyProvider(CurrentProductKeyProvider): ...
```

Tests:

- `tests/apps/gateway/infrastructure/test_institute_cache.py`
- `tests/apps/gateway/infrastructure/test_product_registration_cache.py`
- `tests/apps/gateway/infrastructure/test_current_product_key_provider.py`

Done when:

- current product key can be hydrated internally without exposing it outside the backend

Depends on:

- `C4`, `B3`, `B4`

### Task E3 — Operation session store

Status:

- completed on 2026-03-12

Goal:

- manage pending decoupled operation state safely in memory

Files:

- `apps/gateway/gateway/infrastructure/cache/memory/operation_session_store.py`

Scaffolding:

```python
class InMemoryOperationSessionStore(OperationSessionStore):
    async def create(self, session: PendingOperationSession) -> None: ...
    async def get(self, operation_id: str) -> PendingOperationSession | None: ...
    async def update(self, session: PendingOperationSession) -> None: ...
    async def delete(self, operation_id: str) -> None: ...
    async def expire_stale(self, now: datetime) -> int: ...
```

Tests:

- `tests/apps/gateway/infrastructure/test_operation_session_store.py`
- create/get/update/delete
- expiry sweep
- max-cap enforcement

Done when:

- pending decoupled flow can be resumed and expired safely

Depends on:

- `B5`

### Task E4 — PostgreSQL NOTIFY listener

Status:

- completed on 2026-03-12

Goal:

- keep caches synchronized across gateway instances for persisted state

Files:

- `apps/gateway/gateway/infrastructure/cache/memory/notify_listener.py`

Scaffolding:

```python
class PostgresNotifyListener:
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
```

Tests:

- `tests/apps/gateway/infrastructure/test_notify_listener.py`
- skippable integration test per channel:
  - `gw.consumer_updated`
  - `gw.catalog_replaced`
  - `gw.product_registration_updated`

Done when:

- cache refresh hooks respond correctly to published notifications

Depends on:

- `D3`, `E1`, `E2`

---

## Milestone F — Geldstrom Anti-Corruption Layer

### Task F1 — Connector result models and protocol dispatcher

Status:

- completed on 2026-03-12

Goal:

- define gateway-owned result DTOs and protocol dispatch

Files:

- `apps/gateway/gateway/infrastructure/banking/protocols/dispatcher.py`
- `apps/gateway/gateway/infrastructure/banking/geldstrom/models.py`

Scaffolding:

```python
class BankingConnectorDispatcher:
    def get(self, protocol: BankProtocol) -> BankingConnector: ...
```

Tests:

- `tests/apps/gateway/infrastructure/test_dispatcher.py`
- unknown protocol -> `UnsupportedProtocolError`
- FinTS resolves Geldstrom connector

Done when:

- protocol selection is explicit and isolated

Depends on:

- `B5`, `C1`

### Task F2 — Geldstrom connector implementation

Status:

- completed on 2026-03-12

Goal:

- map gateway requests to Geldstrom calls and translate results/exceptions back

Files:

- `apps/gateway/gateway/infrastructure/banking/geldstrom/connector.py`
- `apps/gateway/gateway/infrastructure/banking/geldstrom/serialization.py`
- `apps/gateway/gateway/infrastructure/banking/geldstrom/exceptions.py`

Scaffolding:

```python
class GeldstromBankingConnector(BankingConnector):
    async def list_accounts(...): ...
    async def fetch_transactions(...): ...
    async def get_tan_methods(...): ...
    async def resume_operation(...): ...
```

Implementation notes:

- obtain the current product key internally through `CurrentProductKeyProvider`
- do not expose product key material in public method signatures
- translate all Geldstrom exceptions to gateway application errors
- serialize session state into opaque bytes for storage

Tests:

- `tests/apps/gateway/infrastructure/test_connector.py`
- exception mapping table coverage
- session-state serialize/deserialize round trip
- completed vs decoupled flows

Done when:

- no Geldstrom type leaks outside the connector boundary

Depends on:

- `F1`, `E2`

---

## Milestone G — Backend Bootstrap and Lifecycle

### Task G1 — Settings and container

Status:

- completed on 2026-03-12

Goal:

- define runtime configuration and dependency factories

Files:

- `apps/gateway/gateway/bootstrap/config.py`
- `apps/gateway/gateway/bootstrap/container.py`

Scaffolding:

```python
class Settings(BaseSettings): ...

def get_settings() -> Settings: ...
def get_db_engine() -> AsyncEngine: ...
def get_api_key_service() -> Argon2ApiKeyService: ...
def get_product_key_service() -> ProductKeyService: ...
def get_current_product_key_provider() -> CurrentProductKeyProvider: ...
# ... remainder of factories
```

Tests:

- `tests/apps/gateway/bootstrap/test_config.py`
- environment loading
- default values

Done when:

- every major component has a single construction path

Depends on:

- `D1`, `D2`, `E1`, `E2`, `E3`, `F2`

### Task G2 — Startup and shutdown lifecycle

Goal:

- initialize caches, background tasks, and DB resources in one place

Files:

- `apps/gateway/gateway/bootstrap/lifecycle.py`

Scaffolding:

```python
async def startup(container) -> None: ...
async def shutdown(container) -> None: ...
```

Tests:

- `tests/apps/gateway/bootstrap/test_lifecycle.py`
- startup warms caches
- startup starts listener and workers
- shutdown cancels them cleanly

Done when:

- the backend can be started and stopped without leaked tasks

Depends on:

- `G1`

### Task G3 — Structured logging bootstrap

Goal:

- enforce secret-safe structured logging from one place

Files:

- `apps/gateway/gateway/bootstrap/logging.py`

Scaffolding:

```python
def configure_logging() -> None: ...
```

Tests:

- `tests/apps/gateway/bootstrap/test_logging.py`
- forbidden fields do not appear
- allowlisted fields do appear

Done when:

- logging defaults are safe before presentation layers are added

Depends on:

- `C1`

---

## Milestone H — FastAPI HTTP App

### Task H1 — FastAPI app and lifespan

Goal:

- expose a runnable HTTP application wired to backend lifecycle

Files:

- `apps/gateway/gateway/presentation/http/api.py`
- `apps/gateway/gateway/bootstrap/container.py`
- `apps/gateway/gateway/main.py`

Scaffolding:

```python
def create_app() -> FastAPI: ...

def main() -> None: ...
```

Tests:

- `tests/apps/gateway/test_app_startup.py`
- app starts with fake backend container

Done when:

- `gateway` entry point resolves and launches

Depends on:

- `G2`

### Task H2 — Request schemas and response schemas

Goal:

- implement the HTTP contract with explicit request/response models

Files:

- `apps/gateway/gateway/presentation/http/schemas/health.py`
- `apps/gateway/gateway/presentation/http/schemas/bank_access.py`
- `apps/gateway/gateway/presentation/http/schemas/accounts.py`
- `apps/gateway/gateway/presentation/http/schemas/transactions.py`
- `apps/gateway/gateway/presentation/http/schemas/tan_methods.py`
- `apps/gateway/gateway/presentation/http/schemas/operations.py`
- `apps/gateway/gateway/presentation/http/schemas/errors.py`

Tests:

- `tests/apps/gateway/test_schemas.py`
- `extra="forbid"` is enforced
- secret-bearing fields use `SecretStr`
- pending operation response includes `polling_interval_seconds`

Done when:

- the HTTP contract matches the architecture document

Depends on:

- `H1`

### Task H3 — Authentication and rate-limit dependencies

Goal:

- implement authenticated request dependencies and consumer-specific rate limiting after auth

Files:

- `apps/gateway/gateway/presentation/http/dependencies.py`
- `apps/gateway/gateway/presentation/http/rate_limit.py`

Scaffolding:

```python
async def get_authenticated_consumer(...) -> AuthenticatedConsumer: ...
async def enforce_consumer_rate_limit(...) -> None: ...
```

Tests:

- `tests/apps/gateway/test_dependencies.py`
- missing API key -> `401`
- disabled consumer -> `403`
- limit exceeded -> `429` with `Retry-After`

Done when:

- consumer-specific limits are applied after authentication

Depends on:

- `C3`, `G1`

### Task H4 — Middleware

Goal:

- add transport-level behavior that does not depend on authenticated identity

Files:

- `apps/gateway/gateway/presentation/http/middleware/request_id.py`
- `apps/gateway/gateway/presentation/http/middleware/no_body_log.py`
- `apps/gateway/gateway/presentation/http/middleware/cache_control.py`
- `apps/gateway/gateway/presentation/http/middleware/exception_handlers.py`

Tests:

- `tests/apps/gateway/test_middleware.py`
- request id echo/generation
- non-health routes get `Cache-Control: no-store`
- exceptions produce `ErrorResponse`

Done when:

- transport concerns are isolated from business use cases

Depends on:

- `H1`, `H2`

### Task H5 — Routers

Goal:

- expose all required HTTP endpoints from the public API contract

Files:

- `apps/gateway/gateway/presentation/http/routers/health.py`
- `apps/gateway/gateway/presentation/http/routers/accounts.py`
- `apps/gateway/gateway/presentation/http/routers/transactions.py`
- `apps/gateway/gateway/presentation/http/routers/tan_methods.py`
- `apps/gateway/gateway/presentation/http/routers/operations.py`

Tests:

- `tests/apps/gateway/test_routes_health.py`
- `tests/apps/gateway/test_routes_accounts.py`
- `tests/apps/gateway/test_routes_transactions.py`
- `tests/apps/gateway/test_routes_tan_methods.py`
- `tests/apps/gateway/test_routes_operations.py`

Required route assertions:

- `GET /health/live`
- `GET /health/ready`
- `POST /v1/banking/accounts`
- `POST /v1/banking/transactions`
- `POST /v1/banking/tan-methods`
- `GET /v1/banking/operations/{operation_id}`
- `200` completed path
- `202` pending path
- `401`, `403`, `404`, `422`, `429` error paths where relevant

Done when:

- the FastAPI app satisfies the documented API shape

Depends on:

- `H2`, `H3`, `H4`, `C5`, `C6`, `C7`, `C8`, `C10`

---

## Milestone I — Typer Admin CLI

### Task I1 — Typer app and entry point

Goal:

- expose a runnable CLI with subcommands

Files:

- `apps/gateway_admin_cli/gateway_admin_cli/presentation/cli/main.py`
- `apps/gateway_admin_cli/gateway_admin_cli/main.py`
- `apps/gateway_admin_cli/gateway_admin_cli/bootstrap/container.py`

Scaffolding:

```python
app = typer.Typer()

def main() -> None: ...
```

Tests:

- `tests/apps/gateway_admin_cli/test_cli_startup.py`
- entry point imports cleanly

Done when:

- `gateway-admin` script resolves correctly

Depends on:

- `G1`

### Task I2 — Consumer admin commands

Goal:

- support consumer create, list, update, disable, delete, and rotate-key flows

Files:

- `apps/gateway_admin_cli/gateway_admin_cli/presentation/cli/commands/consumers.py`
- `apps/gateway_admin_cli/gateway_admin_cli/presentation/cli/formatters/table.py`
- `apps/gateway_admin_cli/gateway_admin_cli/presentation/cli/formatters/json_output.py`

Tests:

- `tests/apps/gateway_admin_cli/test_consumers_cli.py`
- create prints key once
- list prints no secret fields
- update changes email
- disable/delete require confirmation unless `--yes`
- rotate-key prints new key once
- `--json` output serializes correctly

Done when:

- all requested consumer CLI operations are functional

Depends on:

- `I1`, `C11`

### Task I3 — Institute, product-key, and health commands

Goal:

- expose the remaining operator workflows

Files:

- `apps/gateway_admin_cli/gateway_admin_cli/presentation/cli/commands/institutes.py`
- `apps/gateway_admin_cli/gateway_admin_cli/presentation/cli/commands/product_key.py`
- `apps/gateway_admin_cli/gateway_admin_cli/presentation/cli/commands/health.py`

Tests:

- `tests/apps/gateway_admin_cli/test_institutes_cli.py`
- `tests/apps/gateway_admin_cli/test_product_key_cli.py`
- `tests/apps/gateway_admin_cli/test_health_cli.py`

Done when:

- institute sync/inspect, product-key update, and health inspect all work

Depends on:

- `I1`, `C11`

---

## Milestone J — Cross-Cutting Hardening

### Task J1 — Security regression suite

Goal:

- prevent accidental secret leakage over time

Files:

- `tests/apps/gateway/security/test_secret_safety.py`
- `tests/apps/gateway/security/test_http_secret_safety.py`

Tests:

- passwords do not appear in logs
- request bodies are not logged
- `ApplicationError` serialization does not expose secret values
- CLI list/update/inspect flows never output raw API keys or plaintext product keys

Done when:

- explicit secret-safety checks exist at backend and HTTP layer

Depends on:

- `G3`, `H4`, `I2`, `I3`

### Task J2 — Integration smoke slice

Goal:

- verify the real stack wiring through one narrow, realistic happy path

Files:

- `tests/apps/gateway/integration/test_api_smoke.py`
- `tests/apps/gateway_admin_cli/integration/test_cli_smoke.py`

Scenario:

1. create schema in test PostgreSQL
2. sync a tiny institute catalog fixture
3. store a product registration
4. create an API consumer
5. call health endpoint
6. call one banking endpoint using a fake or stub connector wired through the real container

Done when:

- core wiring is proven end-to-end without requiring a real bank

Depends on:

- `H5`, `I3`

---

## Testing Strategy

## 1. Test Pyramid

Use a strict pyramid:

- many unit tests in domain and application layers
- fewer integration tests for PostgreSQL, NOTIFY, lifecycle, and HTTP wiring
- very few end-to-end smoke tests
- bank-integration tests remain optional and skippable

Target distribution:

- 70–80% unit tests
- 15–25% integration tests
- 5% end-to-end smoke tests

## 2. Test Types by Layer

### Domain tests

Scope:

- value objects
- aggregates
- domain services
- no fakes needed unless useful for convenience

Rules:

- no database
- no FastAPI
- no Geldstrom
- run fastest and most often

### Application tests

Scope:

- use case orchestration
- error mapping at use-case boundary
- pending/completed/failed/expired operation state handling

Rules:

- only fake ports
- deterministic time via fake `IdProvider`
- deterministic connector behavior via fake connector states

### Infrastructure tests

Scope:

- crypto services
- repositories
- caches
- notify listener
- anti-corruption connector mapping

Rules:

- split into pure unit tests and skippable integration tests
- PostgreSQL tests use a disposable DB
- NOTIFY tests require a live PostgreSQL connection

### Presentation tests

Scope:

- request validation
- error responses
- status code mapping
- CLI output formatting and confirmation behavior

Rules:

- FastAPI tests use `httpx.AsyncClient`
- CLI tests use `typer.testing.CliRunner`
- prefer fake backend dependencies for router/command tests

## 3. Pytest Markers

Recommended markers:

```toml
[tool.pytest.ini_options]
markers = [
    "integration: requires external services such as PostgreSQL",
    "bank: requires access to a real bank or real protocol test target",
    "slow: slower-running tests that are not required on every edit",
]
```

Usage:

- default local loop: run unit tests only
- CI default: run unit + integration
- explicit manual run: bank tests only when intentionally requested

## 4. Fixture Strategy

Create reusable fixtures for:

- active and disabled `ApiConsumer`
- canonical and duplicate `FinTSInstitute`
- encrypted product registration
- decoupled pending session
- fixed timestamps and deterministic UUIDs
- fake connector scenarios

Avoid oversized fixtures.

Prefer small explicit fixture builders over giant global test data blobs.

## 5. CI Test Stages

Recommended stages:

1. `lint`
   - Ruff
2. `unit`
   - domain + application + pure infrastructure tests
3. `integration`
   - PostgreSQL repositories + NOTIFY + lifecycle + HTTP smoke
4. `security`
   - explicit secret-safety regression suite
5. optional `bank`
   - real bank/protocol tests only when enabled

## 6. Minimum Test Commands During Development

Recommended smallest commands by work area:

### Domain work

```bash
uv run pytest tests/apps/gateway/domain/
```

### Application work

```bash
uv run pytest tests/apps/gateway/application/
```

### Repository work

```bash
uv run pytest tests/apps/gateway/infrastructure/test_*repository.py -m integration
```

### HTTP work

```bash
uv run pytest tests/apps/gateway/
```

### CLI work

```bash
uv run pytest tests/apps/gateway_admin_cli/
```

## 7. Definition of Done for the Whole Gateway v1

The implementation is ready for first release only when all of the following are true:

- all milestone tasks through `I3` are complete
- `J1` security regression tests are green
- `GET /health/live` and `GET /health/ready` behave as documented
- accounts, transactions, tan-methods, and operation-status routes behave as documented
- admin CLI supports create, list, update, disable, delete, rotate-key, institute sync, product-key update, and health inspect
- no plaintext bank credentials, API keys, or product keys appear in logs or API responses
- the current FinTS product key is settable through the admin CLI and usable by the banking connector without being externally readable
- one narrow end-to-end smoke test passes against the real container wiring

---

## Suggested Implementation Order

If only one engineer is working on the gateway, use this order:

1. `A1`, `A2`
2. `B1` to `B5`
3. `C1`, `C2`, `C3`, `C4`
4. `C5`, `C6`, `C7`, `C8`, `C9`, `C10`
5. `D1`, `D2`, `E1`, `E2`, `E3`
6. `C11`
7. `D3`, `D4`, `D5`, `D6`, `D7`, `E4`
8. `F1`, `F2`
9. `G1`, `G2`, `G3`
10. `H1` to `H5`
11. `I1` to `I3`
12. `J1`, `J2`

If two engineers are working in parallel:

- Engineer A:
  - domain + application path (`B*`, `C*`)
- Engineer B:
  - crypto + persistence + caches (`D*`, `E*`)

Merge point:

- anti-corruption layer and bootstrap (`F*`, `G*`)

Then split again:

- Engineer A: HTTP (`H*`)
- Engineer B: CLI + hardening (`I*`, `J*`)
