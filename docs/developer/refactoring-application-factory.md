# Refactoring Plan: Unified ApplicationFactory

## Goal

Replace the flat collection of `@lru_cache` functions in `container.py` with a structured
`ApplicationFactory` design: three composable port interfaces in the application layer
(`RepositoryFactory`, `CacheFactory`, `ApplicationFactory`) and one concrete infrastructure
implementation (`GatewayApplicationFactory`) that also owns the notify listener and lifecycle.

**Benefits:**
- Container.py collapses from ~400 lines to ~80 lines
- All use cases get a `from_factory(factory)` classmethod — wiring is co-located with the use case
- Natural separation of persistence (`RepositoryFactory`) from in-memory state (`CacheFactory`)
- Clear boundary: the application layer only sees the three port interfaces (no infrastructure types leak through)
- Testing: stub only the sub-factory relevant to the use case under test

---

## Design Overview

```
application/ports/repository_factory.py   ─┐
application/ports/cache_factory.py         ├─ Protocols (what use cases see)
application/ports/application_factory.py  ─┘
         │
         ▼ implements
infrastructure/gateway_factory.py          ← GatewayApplicationFactory
                                             (concrete, nests both sub-factories,
                                              adds notify listener + lifecycle)
         │
         ▼ instantiated by
bootstrap/container.py                     ← get_factory() → GatewayApplicationFactory
                                             get_<use_case>_use_case() → UseCase.from_factory(get_factory())
```

The application layer has **no** knowledge of `PostgresNotifyListener`, `AsyncEngine`,
`InMemory*Cache`, argon2, etc. `GatewayApplicationFactory` is a purely infrastructure concern.

---

## Three Port Interfaces

### Naming Convention

**All factory accessors are `@property`** throughout — on `ApplicationFactory`, `RepositoryFactory`,
and `CacheFactory`. This is the most Pythonic style and reads naturally: `factory.repos.consumer`
is accessing a wired service object, which is exactly what it is. Plain methods like `consumer()`
or prefixed `get_consumer()` add noise without benefit, and double-call syntax like
`factory.repos().consumer()` is awkward.

Python's `typing.Protocol` has fully supported `@property` since 3.8. All concrete
implementations use `@cached_property`, so there is no hidden cost to the accessor pattern.

### 1. `RepositoryFactory` — `application/ports/repository_factory.py`

Groups all database-backed ports.

```python
class RepositoryFactory(Protocol):
    @property
    def consumer(self) -> ApiConsumerRepository: ...
    @property
    def institute(self) -> FinTSInstituteRepository: ...
    @property
    def product_registration(self) -> FinTSProductRegistrationRepository: ...
```

### 2. `CacheFactory` — `application/ports/cache_factory.py`

Groups all in-memory state. Each property returns a **merged** cache protocol (Option A):
the return type satisfies both the read-aspect port and the write-aspect port of that cache,
allowing individual use cases to structurally narrow to the slice they need in their `__init__`.

```python
class ConsumerCache(ConsumerCachePort, ConsumerCacheWriter, Protocol): ...
class InstituteCache(InstituteCatalogPort, InstituteCacheLoader, Protocol): ...
class ProductKeyCache(CurrentProductKeyProvider, CurrentProductKeyLoader, Protocol): ...
class ProductRegistrationCache(ProductRegistrationCachePort, Protocol): ...

class CacheFactory(Protocol):
    @property
    def consumer(self) -> ConsumerCache: ...
    @property
    def institute(self) -> InstituteCache: ...
    @property
    def product_key(self) -> ProductKeyCache: ...
    @property
    def product_registration(self) -> ProductRegistrationCache: ...
    @property
    def session_store(self) -> PendingOperationRuntimeStore: ...
```

The merged protocols (`ConsumerCache`, etc.) are defined in the same file.
`InMemoryApiConsumerCache` already implements both `ConsumerCachePort` and `ConsumerCacheWriter`
— Python structural typing means no changes to the infrastructure class.

### 3. `ApplicationFactory` — `application/ports/application_factory.py`

The single entry point visible to all use cases. Nests the two sub-factories and adds
the remaining cross-cutting services. **All accessors are properties.**

```python
class ApplicationFactory(Protocol):
    @property
    def repos(self) -> RepositoryFactory: ...
    @property
    def caches(self) -> CacheFactory: ...

    # --- Crypto ---
    @property
    def api_key_service(self) -> ApiKeyService: ...         # generate + hash (admin use cases)
    @property
    def api_key_verifier(self) -> ApiKeyVerifier: ...       # verify only (AuthenticateConsumer) — already a domain port
    @property
    def product_key_encryptor(self) -> ProductKeyEncryptor: ...  # encrypt (UpdateProductRegistration) — NEW port

    # --- Banking ---
    @property
    def banking_connector(self) -> BankingConnector: ...    # already a domain port

    # --- Utilities ---
    @property
    def id_provider(self) -> IdProvider: ...
    @property
    def institute_csv_reader(self) -> InstituteCsvReaderPort: ...  # stateless, no caching

    # --- Health ---
    @property
    def readiness_checks(self) -> Mapping[str, ReadinessCheck]: ...
```

Config scalars (`product_version`, `key_version`) are **not** on the factory — they are
passed as additional keyword arguments to `UpdateProductRegistration.from_factory()`.
Factories supply *objects*, not configuration strings.

---

## New Ports Needed

### `ProductKeyEncryptor` — `application/administration/ports/product_key_encryptor.py`

`UpdateProductRegistration.product_key_service` currently has no type annotation (leaked
infrastructure type). This port fixes it:

```python
class ProductKeyEncryptor(Protocol):
    def encrypt(self, plaintext: str) -> EncryptedProductKey: ...
```

`ProductKeyService` (infrastructure) already satisfies this structurally — no change needed there.

### Merged cache protocols — defined in `application/ports/cache_factory.py`

`ConsumerCache`, `InstituteCache`, `ProductKeyCache` are thin merged protocols:

```python
class ConsumerCache(ConsumerCachePort, ConsumerCacheWriter, Protocol): ...
class InstituteCache(InstituteCatalogPort, InstituteCacheLoader, Protocol): ...
class ProductKeyCache(CurrentProductKeyProvider, CurrentProductKeyLoader, Protocol): ...
```

These replace no existing code — they are new names for the combined shape already
implemented by the infrastructure classes.

---

## GatewayApplicationFactory (Concrete Implementation)

Lives at `infrastructure/gateway_factory.py`. Implements `ApplicationFactory` and nests
two concrete inner classes implementing `RepositoryFactory` and `CacheFactory`.

```python
class GatewayApplicationFactory:
    def __init__(self, settings: Settings) -> None: ...

    # ApplicationFactory protocol surface — all @cached_property
    @cached_property
    def repos(self) -> _SQLAlchemyRepositoryFactory: ...

    @cached_property
    def caches(self) -> _InMemoryCacheFactory: ...

    @cached_property
    def api_key_service(self) -> Argon2ApiKeyService: ...

    @cached_property
    def api_key_verifier(self) -> Argon2ApiKeyService: ...      # same object, narrowed

    @cached_property
    def product_key_encryptor(self) -> ProductKeyService: ...

    @cached_property
    def banking_connector(self) -> GeldstromBankingConnector: ...

    @cached_property
    def id_provider(self) -> IdProvider: ...

    @cached_property
    def institute_csv_reader(self) -> InstituteCsvReader: ...

    @property
    def readiness_checks(self) -> Mapping[str, ReadinessCheck]: ...  # re-builds dict each call (lightweight)

    # Lifecycle (NOT on the port — application layer doesn't know about these)
    async def startup(self) -> None: ...
    async def shutdown(self) -> None: ...


class _SQLAlchemyRepositoryFactory:
    """Implements RepositoryFactory — all Postgres-backed."""
    def __init__(self, engine: AsyncEngine) -> None: ...
    @cached_property
    def consumer(self) -> PostgresApiConsumerRepository: ...
    @cached_property
    def institute(self) -> PostgresFinTSInstituteRepository: ...
    @cached_property
    def product_registration(self) -> PostgresFinTSProductRegistrationRepository: ...


class _InMemoryCacheFactory:
    """Implements CacheFactory — all in-memory."""
    def __init__(self, settings: Settings) -> None: ...
    @cached_property
    def consumer(self) -> InMemoryApiConsumerCache: ...         # satisfies ConsumerCache merged protocol
    @cached_property
    def institute(self) -> InMemoryFinTSInstituteCache: ...
    @cached_property
    def product_key(self) -> InMemoryCurrentProductKeyProvider: ...
    @cached_property
    def product_registration(self) -> InMemoryProductRegistrationCache: ...
    @cached_property
    def session_store(self) -> InMemoryOperationSessionStore: ...
```

**Why no port for `PostgresNotifyListener`?**

The application layer never calls the listener — it only calls the caches. The listener is
the *mechanism* by which caches stay fresh, but that mechanism is entirely invisible to use
cases. No use case does `notify_listener.start()` or `notify_listener.handle_event()`.

The caches *are* the ports. How they get invalidated is an implementation detail inside
`GatewayApplicationFactory`. In tests, you use a stub factory whose caches return
fixed values — cache invalidation is irrelevant. There is nothing for a
`NotifyListenerPort` to abstract over from the application layer's perspective.

Analogy: a DB connection pool keeps connections alive, but there is no `ConnectionPoolPort`
in the application layer — you just have a `UserRepository` port. Same principle here.

`_RuntimeIdProvider` becomes a private class at the top of `gateway_factory.py`.

`startup()` and `shutdown()` encapsulate all logic currently in `lifecycle.py`'s private helpers.

---

## `from_factory()` on Use Cases

Every use case gains an **additional** classmethod. `__init__` is unchanged (tests are unaffected).

**Pattern:**
```python
@classmethod
def from_factory(cls, factory: ApplicationFactory) -> Self:
    return cls(
        authenticate_consumer=AuthenticateConsumer.from_factory(factory),
        institute_catalog=factory.caches.institute,
        current_product_key_provider=factory.caches.product_key,
        connector=factory.banking_connector,
        session_store=factory.caches.session_store,
        id_provider=factory.id_provider,
    )
```

**Full mapping:**

| Use case | Dependencies |
|---|---|
| `AuthenticateConsumer` | `caches.consumer` · `api_key_verifier` |
| `ListAccounts` | `AuthenticateConsumer.from_factory()` · `caches.institute` · `caches.product_key` · `banking_connector` · `caches.session_store` · `id_provider` |
| `FetchHistoricalTransactions` | same as ListAccounts |
| `GetAllowedTanMethods` | same as ListAccounts |
| `GetOperationStatus` | `AuthenticateConsumer.from_factory()` · `caches.session_store` · `id_provider` |
| `ResumePendingOperations` | `caches.session_store` · `banking_connector` · `id_provider` |
| `CreateApiConsumer` | `repos.consumer` · `caches.consumer` · `api_key_service` · `id_provider` |
| `UpdateApiConsumer` | `repos.consumer` · `caches.consumer` |
| `RotateApiConsumerKey` | `repos.consumer` · `caches.consumer` · `api_key_service` · `id_provider` |
| `DisableApiConsumer` | `repos.consumer` · `caches.consumer` |
| `DeleteApiConsumer` | `repos.consumer` · `caches.consumer` |
| `ListApiConsumers` | `repos.consumer` |
| `SyncInstituteCatalog` | `institute_csv_reader` · `repos.institute` · `caches.institute` |
| `UpdateProductRegistration` | `repos.product_registration` · `caches.product_registration` · `caches.product_key` · `product_key_encryptor` · `id_provider` + kwargs `product_version`, `key_version` |
| `InspectBackendState` | `EvaluateHealth.from_factory(factory)` · `repos.consumer` · `repos.institute` · `repos.product_registration` |
| `EvaluateHealth` | `readiness_checks` |

---

## Resulting container.py

```python
@lru_cache(maxsize=1)
def get_factory() -> GatewayApplicationFactory:
    return GatewayApplicationFactory(get_settings())

@lru_cache(maxsize=1)
def get_authenticate_consumer_use_case() -> AuthenticateConsumer:
    return AuthenticateConsumer.from_factory(get_factory())

@lru_cache(maxsize=1)
def get_list_accounts_use_case() -> ListAccounts:
    return ListAccounts.from_factory(get_factory())

# ... 14 more, all identical pattern

def reset_container_state() -> None:
    get_settings.cache_clear()
    get_factory.cache_clear()
    get_authenticate_consumer_use_case.cache_clear()
    # ... ~18 lines total instead of 35
```

---

## Resulting lifecycle.py

```python
from .container import get_factory

async def startup() -> None:
    await get_factory().startup()

async def shutdown() -> None:
    await get_factory().shutdown()

async def run_resume_worker(*, interval_seconds: float = 5.0) -> None:
    # unchanged — background loop concern, not a factory concern
    ...
```

---

## Implementation Steps

1. **New ports** — create `application/ports/repository_factory.py`, `cache_factory.py`, `application_factory.py`
2. **Missing port** — `application/administration/ports/product_key_encryptor.py`; type-annotate `UpdateProductRegistration.product_key_service`
3. **`GatewayApplicationFactory`** — create `infrastructure/gateway_factory.py` with `_SQLAlchemyRepositoryFactory`, `_InMemoryCacheFactory`, `GatewayApplicationFactory`; move `_RuntimeIdProvider` and `_check_*` health functions here; implement `startup()` / `shutdown()`
4. **`from_factory()` classmethods** — add to all 16 use case files
5. **Rewrite `container.py`** — one `get_factory()` + 16 one-liner use case getters
6. **Slim `lifecycle.py`** — delegate `startup()` / `shutdown()` to factory; keep `run_resume_worker()`
7. **Run full test suite** — fix any import or type errors

---

## What Does NOT Change

- All `__init__` signatures on use cases (all existing unit tests remain valid)
- All existing per-context ports in `application/*/ports/` (they are imported by the new merged protocols)
- The HTTP presentation layer (container still exposes named `get_X_use_case()` functions for `Depends()`)
- `PostgresNotifyListener` itself (no logic changes)

---

## Decisions Log

| Question | Decision |
|---|---|
| One factory or nested? | `ApplicationFactory` nests `RepositoryFactory` and `CacheFactory` as `.repos` / `.caches` properties |
| Cache read/write split? | Option A — one property per cache returning a merged protocol; `__init__` params accept the narrow slice they need via structural typing |
| Config scalars on factory? | No — factories supply objects only; `product_version` / `key_version` are extra kwargs to `from_factory()` |
| `NotifyListener` port? | No port needed — the application layer never interacts with the listener; caches are the ports; invalidation is an infrastructure detail |
| `NotifyListener` ownership? | Owned internally by `GatewayApplicationFactory`, used only in `startup()` / `shutdown()` |
| Accessor style? | All `@property` / `@cached_property` throughout — on all three port protocols and both concrete sub-factories. No `get_X()` methods, no bare `X()` call syntax |
| `_RuntimeIdProvider` location? | Private class at top of `infrastructure/gateway_factory.py` |
| `InstituteCsvReader` caching? | `@cached_property` in factory (stateless, but consistent with everything else) |
| `from_factory()` signature? | Single argument: `from_factory(factory: ApplicationFactory)`, plus explicit kwargs for config scalars |
