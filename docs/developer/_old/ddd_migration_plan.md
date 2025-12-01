# Domain-Driven Design Migration Plan

## Overview

This document outlines the plan to refactor the `python-fints` package to follow Domain-Driven Design (DDD) principles. The goal is to create a clean separation where:

- **Domain Layer**: Contains protocol-agnostic banking models and connection abstractions
- **Infrastructure Layer**: Implements specific protocols (FinTS 3.0 initially, with room for PSD2/EBICS in the future)
- **Application Layer**: Orchestrates use cases using domain ports

## Current State Assessment

### ✅ Completed Work

#### Domain Layer (`fints/domain/`)

Well-structured with protocol-agnostic models:

```
fints/domain/
├── __init__.py              # Public exports
├── connection/
│   ├── __init__.py
│   ├── challenge.py         # ChallengeType, ChallengeData, Challenge (ABC)
│   ├── credentials.py       # BankCredentials
│   ├── retry.py             # NeedRetryResponse (ABC), ResponseStatus
│   └── session.py           # SessionHandle
├── model/
│   ├── __init__.py
│   ├── accounts.py          # Account, AccountOwner, AccountCapabilities
│   ├── balances.py          # BalanceAmount, BalanceSnapshot
│   ├── bank.py              # BankRoute, BankCapabilities
│   ├── payments.py          # PaymentInstruction, PaymentConfirmation
│   ├── statements.py        # StatementDocument, StatementReference
│   └── transactions.py      # TransactionEntry, TransactionFeed
└── ports/
    ├── __init__.py
    ├── accounts.py          # AccountDiscoveryPort
    ├── balances.py          # BalancePort
    ├── payments.py          # PaymentPort
    ├── session.py           # SessionPort
    ├── statements.py        # StatementPort
    └── transactions.py      # TransactionHistoryPort
```

#### Application Layer (`fints/application/`)

Use-case services that orchestrate domain operations:

- `AccountDiscoveryService`
- `BalanceService`
- `TransactionHistoryService`
- `GatewayCredentials` (DTO combining domain credentials with infrastructure details)
- `BankGateway` (protocol for infrastructure adapters)

#### Infrastructure Layer (`fints/infrastructure/`)

Partial implementation:

```
fints/infrastructure/
├── __init__.py
├── gateway.py               # FinTSReadOnlyGateway (wraps legacy client)
├── fints/
│   ├── __init__.py
│   ├── operations.py        # FinTSOperations enum
│   ├── responses.py         # FinTS-specific NeedRetryResponse, TransactionResponse
│   ├── session.py           # SessionState (FinTS-specific)
│   └── services/
│       ├── __init__.py
│       ├── statements.py    # StatementsService
│       └── transactions.py  # TransactionsService
└── legacy/
    ├── __init__.py
    ├── dialog_manager.py    # DialogSessionManager
    ├── pintan.py            # PinTanWorkflow
    ├── tan.py               # NeedTANResponse, IMPLEMENTED_HKTAN_VERSIONS
    └── touchdown.py         # TouchdownPaginator
```

#### Read-Only Client (`fints/readonly/`)

Working high-level API demonstrating the architecture:

- `ReadOnlyFinTSClient` - Uses services and gateway

### ⚠️ Issues to Address

1. ~~**SessionState Dependency Inversion Violation**~~ ✅ RESOLVED
   - ~~`SessionState` lives in `fints/infrastructure/fints/session.py`~~
   - ~~Domain ports import it directly, creating coupling~~
   - ~~Domain layer should not depend on infrastructure~~
   - **Solution**: Created `SessionToken` protocol in domain, domain ports use protocol

2. **Gateway Wraps Legacy Client**
   - `FinTSReadOnlyGateway` delegates to `FinTS3PinTanClient`
   - Legacy client (~1000 LOC) is still the core implementation

3. **Legacy Client is Monolithic**
   - Dialog lifecycle management
   - TAN workflow coordination
   - Business operations (balance, transactions, transfers)
   - State serialization/deserialization
   - Response processing

4. **Domain Ports Lack Direct Implementations**
   - Ports exist but only `BankGateway` (application layer) is implemented
   - No direct infrastructure implementations of domain ports

---

## Migration Phases

### Phase 1: Fix Domain Layer Dependencies ✅ COMPLETED

**Duration**: 1-2 days (Completed: Nov 28, 2025)
**Priority**: High
**Goal**: Ensure domain layer is truly protocol-agnostic

#### Tasks

- [x] **1.1** Create `SessionToken` protocol in domain layer
  - Location: `fints/domain/connection/session.py`
  - Define minimal interface for session state
  - Make `SessionHandle` implement this protocol

- [x] **1.2** Update `SessionPort` to use `SessionToken` protocol
  - Location: `fints/domain/ports/session.py`
  - Replace `SessionState` import with `SessionToken`

- [x] **1.3** Rename `SessionState` to `FinTSSessionState`
  - Location: `fints/infrastructure/fints/session.py`
  - Implement `SessionToken` protocol
  - Update all infrastructure imports
  - Keep `SessionState` as backward-compatible alias

- [x] **1.4** Update domain port imports
  - All domain ports now use `SessionToken` from domain
  - No domain files import from infrastructure

- [x] **1.5** Update application layer
  - `BankGateway` protocol uses `SessionToken`
  - Application services use `SessionToken`

- [x] **1.6** Update readonly client and examples
  - `ReadOnlyFinTSClient` uses `SessionToken`
  - Example updated to use `FinTSSessionState` for serialization

#### Target Structure

```python
# fints/domain/connection/session.py
from typing import Protocol, Any

class SessionToken(Protocol):
    """Protocol-agnostic session interface."""

    @property
    def user_id(self) -> str:
        """User identifier for this session."""
        ...

    @property
    def is_expired(self) -> bool:
        """Whether the session has expired."""
        ...

    def serialize(self) -> bytes:
        """Serialize session for storage/resumption."""
        ...

    @classmethod
    def deserialize(cls, data: bytes) -> "SessionToken":
        """Restore session from serialized data."""
        ...


# Existing SessionHandle can remain for generic use
class SessionHandle(BaseModel, frozen=True):
    """Lightweight session representation."""
    ...
```

```python
# fints/infrastructure/fints/session.py
from fints.domain.connection.session import SessionToken

@dataclass(frozen=True)
class FinTSSessionState:
    """FinTS 3.0-specific session implementation."""
    route: BankRoute
    user_id: str
    system_id: str
    client_blob: bytes
    bpd_version: int | None = None
    upd_version: int | None = None
    created_at: datetime = field(default_factory=...)
    version: str = "1"

    # Implements SessionToken protocol
    @property
    def is_expired(self) -> bool:
        # FinTS sessions don't typically expire on their own
        return False

    def serialize(self) -> bytes:
        return compress_datablob(...)

    @classmethod
    def deserialize(cls, data: bytes) -> "FinTSSessionState":
        return cls.from_dict(decompress_datablob(...))
```

---

### Phase 2: Extract Dialog Infrastructure ✅ COMPLETED

**Duration**: 3-5 days (Completed: Nov 28, 2025)
**Priority**: High
**Goal**: Move dialog/transport logic from `client.py` into clean infrastructure modules

#### Tasks

- [x] **2.1** Create dialog connection module
  - Location: `fints/infrastructure/fints/dialog/connection.py`
  - `DialogConnection` protocol for transport abstraction
  - `HTTPSDialogConnection` implementation with base64 encoding
  - `ConnectionConfig` dataclass for configuration

- [x] **2.2** Create message transport module
  - Location: `fints/infrastructure/fints/dialog/transport.py`
  - `MessageTransport` protocol
  - `FinTSMessageTransport` for message construction/sending
  - Message number tracking

- [x] **2.3** Create response processing module
  - Location: `fints/infrastructure/fints/dialog/responses.py`
  - `ResponseProcessor` for parsing HIRMG/HIRMS segments
  - `ProcessedResponse` dataclass with BPD/UPD extraction
  - `DialogResponse` for individual response codes
  - Callback system for response handling

- [x] **2.4** Create protocol parameters module
  - Location: `fints/infrastructure/fints/protocol/parameters.py`
  - `BankParameters` for BPD management
  - `UserParameters` for UPD management
  - `ParameterStore` for session parameter caching
  - Serialization/deserialization support

- [x] **2.5** Create dialog factory
  - Location: `fints/infrastructure/fints/dialog/factory.py`
  - `Dialog` class for active session management
  - `DialogFactory` for creating dialogs with proper lifecycle
  - `DialogConfig` and `DialogState` dataclasses
  - Context manager support for automatic cleanup

#### Target Structure

```
fints/infrastructure/fints/
├── __init__.py
├── dialog/
│   ├── __init__.py
│   ├── connection.py      # HTTP transport, timeout/retry
│   ├── factory.py         # Dialog creation and lifecycle
│   ├── messages.py        # Message construction helpers
│   ├── responses.py       # Response parsing, HIRMG/HIRMS handling
│   └── transport.py       # Send/receive, encryption, compression
├── protocol/
│   ├── __init__.py
│   ├── parameters.py      # BPD/UPD management
│   └── segments.py        # Segment factory/registry
├── services/              # (existing)
├── operations.py          # (existing)
├── responses.py           # (existing, may merge with dialog/responses.py)
└── session.py             # (rename to FinTSSessionState)
```

#### Key Interfaces

```python
# fints/infrastructure/fints/dialog/connection.py
class DialogConnection(Protocol):
    """Interface for FinTS dialog transport."""

    def send(self, message: bytes) -> bytes:
        """Send message and receive response."""
        ...

    def close(self) -> None:
        """Close the connection."""
        ...


class HTTPSDialogConnection:
    """HTTPS implementation of DialogConnection."""

    def __init__(self, url: str, timeout: float = 30.0):
        self._url = url
        self._timeout = timeout

    def send(self, message: bytes) -> bytes:
        # ... HTTP POST logic
        pass
```

```python
# fints/infrastructure/fints/dialog/factory.py
class DialogFactory:
    """Creates and manages FinTS dialog instances."""

    def __init__(
        self,
        connection: DialogConnection,
        parameters: BankParameters,
        auth_mechanism: AuthenticationMechanism,
    ):
        self._connection = connection
        self._parameters = parameters
        self._auth = auth_mechanism

    @contextmanager
    def open(self, session: FinTSSessionState) -> Iterator[Dialog]:
        """Open a dialog for the given session."""
        dialog = Dialog(...)
        try:
            dialog.initialize()
            yield dialog
        finally:
            dialog.close()
```

---

### Phase 3: Extract TAN Workflow ✅ COMPLETED

**Duration**: 3-5 days (Completed: Nov 28, 2025)
**Priority**: High
**Goal**: Clean separation of TAN handling from business operations

#### Completed Tasks

- [x] **3.1** Enhance domain challenge types
  - Location: `fints/domain/connection/challenge.py`
  - Added `ChallengeHandler` protocol for presenting challenges
  - Added `DecoupledPoller` protocol for async confirmation
  - Added `ChallengeResult` dataclass
  - Added `InteractiveChallengeHandler` default implementation

- [x] **3.2** Create authentication module structure
  - Location: `fints/infrastructure/fints/auth/`
  - Created `__init__.py` with public exports
  - Organized TAN-related code into focused modules

- [x] **3.3** Extract PIN/TAN workflow
  - Location: `fints/infrastructure/fints/auth/workflow.py`
  - `PinTanWorkflow` class with TAN mechanism management
  - `TanWorkflowConfig` dataclass
  - `IMPLEMENTED_HKTAN_VERSIONS` mapping

- [x] **3.4** Extract TAN media discovery
  - Location: `fints/infrastructure/fints/auth/tan_media.py`
  - `TanMediaDiscovery` class for querying available media
  - `TanMediaInfo` dataclass

- [x] **3.5** Create security mechanism module
  - Location: `fints/infrastructure/fints/auth/mechanisms.py`
  - `EncryptionMechanism` and `AuthenticationMechanism` protocols
  - `PinTanDummyEncryptionMechanism`
  - `PinTanOneStepAuthenticationMechanism`
  - `PinTanTwoStepAuthenticationMechanism`

- [x] **3.6** Create decoupled polling utility
  - Location: `fints/infrastructure/fints/auth/decoupled.py`
  - `DecoupledConfirmationPoller` with configurable polling
  - `DecoupledPollingConfig` dataclass

- [x] **3.7** Extract challenge parsing
  - Location: `fints/infrastructure/fints/auth/challenge.py`
  - `NeedTANResponse` (implements domain Challenge)
  - `FinTSChallenge` wrapper class
  - `parse_tan_challenge` function for HHD_UC/matrix parsing

- [x] **3.8** Migrate client to new auth modules
  - Updated `fints/infrastructure/legacy/__init__.py` to re-export from new auth module
  - Converted `legacy/tan.py` and `legacy/pintan.py` to thin deprecated re-export wrappers
  - Client imports unchanged (backward compatible)
  - All unit and integration tests pass

#### Target Structure

```
fints/infrastructure/fints/auth/
├── __init__.py
├── challenge.py       # FinTS-specific NeedTANResponse, challenge parsing
├── decoupled.py       # Decoupled TAN polling logic
├── mechanisms.py      # PinTanDummyEncryption, OneStep/TwoStep auth
├── pintan.py          # PIN/TAN workflow orchestration
└── tan_media.py       # TAN media discovery (HKTAB)
```

#### Key Interfaces

```python
# fints/domain/connection/challenge.py (additions)
class ChallengeHandler(Protocol):
    """Protocol for handling 2FA challenges."""

    def present(self, challenge: Challenge) -> str | None:
        """
        Present challenge to user and get response.

        Returns TAN string for interactive flows, None for decoupled.
        """
        ...

    def poll_decoupled(
        self,
        challenge: Challenge,
        interval: float = 2.0,
        timeout: float = 120.0,
    ) -> bool:
        """
        Poll for decoupled confirmation.

        Returns True if confirmed, raises TimeoutError if timeout exceeded.
        """
        ...
```

```python
# fints/infrastructure/fints/auth/pintan.py
class PinTanAuthenticator:
    """Handles PIN/TAN authentication flows for FinTS 3.0."""

    def __init__(
        self,
        pin: str,
        security_function: str | None = None,
        tan_medium: str | None = None,
    ):
        self._pin = pin
        self._security_function = security_function
        self._tan_medium = tan_medium

    def create_mechanisms(self) -> tuple[EncryptionMechanism, list[AuthMechanism]]:
        """Create encryption and authentication mechanisms for dialog."""
        ...

    def handle_tan_required(
        self,
        dialog: Dialog,
        command: Segment,
        challenge_handler: ChallengeHandler,
    ) -> Response:
        """Handle TAN requirement for a command."""
        ...
```

---

### Phase 4: Implement Domain Ports ✅ COMPLETED

**Duration**: 5-7 days (Completed: Nov 28, 2025)
**Priority**: Medium
**Goal**: Create infrastructure implementations of domain ports

#### Completed Tasks

- [x] **4.1** Implement `SessionPort` adapter
  - Location: `fints/infrastructure/fints/adapters/session.py`
  - `FinTSSessionAdapter` class
  - Handles session open/close via legacy client

- [x] **4.2** Implement `AccountDiscoveryPort` adapter
  - Location: `fints/infrastructure/fints/adapters/accounts.py`
  - `FinTSAccountDiscovery` class
  - Fetches accounts and bank capabilities

- [x] **4.3** Implement `BalancePort` adapter
  - Location: `fints/infrastructure/fints/adapters/balances.py`
  - `FinTSBalanceAdapter` class
  - MT940 balance parsing

- [x] **4.4** Implement `TransactionHistoryPort` adapter
  - Location: `fints/infrastructure/fints/adapters/transactions.py`
  - `FinTSTransactionHistory` class
  - Supports both MT940 (HKKAZ) and CAMT (HKCAZ) formats
  - Includes decoupled TAN handling

- [x] **4.5** Implement `StatementPort` adapter
  - Location: `fints/infrastructure/fints/adapters/statements.py`
  - `FinTSStatementAdapter` class
  - Statement listing and retrieval

- [ ] **4.6** Implement `PaymentPort` adapter (optional for read-only)
  - Location: `fints/infrastructure/fints/adapters/payments.py`
  - HKCCS, HKDSE operations
  - SEPA XML generation
  - *Skipped for now - not needed for read-only operations*

#### Implemented Structure

```
fints/infrastructure/fints/adapters/
├── __init__.py        # Exports all adapters
├── accounts.py        # FinTSAccountDiscovery (AccountDiscoveryPort)
├── balances.py        # FinTSBalanceAdapter (BalancePort)
├── session.py         # FinTSSessionAdapter (SessionPort)
├── statements.py      # FinTSStatementAdapter (StatementPort)
└── transactions.py    # FinTSTransactionHistory (TransactionHistoryPort)
```

Note: `payments.py` skipped for read-only operations.

#### Key Interfaces

```python
# fints/infrastructure/fints/adapters/balances.py
from fints.domain.ports.balances import BalancePort
from fints.domain import BalanceSnapshot

class FinTSBalanceAdapter(BalancePort):
    """FinTS 3.0 implementation of BalancePort."""

    def __init__(self, dialog_factory: DialogFactory):
        self._dialog_factory = dialog_factory

    def fetch_balances(
        self,
        session: FinTSSessionState,
        account_ids: Sequence[str] | None = None,
    ) -> Sequence[BalanceSnapshot]:
        with self._dialog_factory.open(session) as dialog:
            hksal = self._select_hksal_version(dialog.parameters)
            results = []
            for account_id in (account_ids or self._all_account_ids(session)):
                segment = hksal(
                    account=self._resolve_account(account_id),
                    all_accounts=False,
                )
                response = dialog.send(segment)
                balance = self._parse_hisal(response)
                results.append(balance)
            return results

    def _select_hksal_version(self, params: BankParameters) -> type:
        """Select highest supported HKSAL version."""
        ...

    def _parse_hisal(self, response: Response) -> BalanceSnapshot:
        """Parse HISAL segment into domain model."""
        ...
```

---

### Phase 5: Create New Client Facade ✅ COMPLETED

**Duration**: 2-3 days (Completed: Nov 28, 2025)
**Priority**: Medium
**Goal**: Replace `FinTS3PinTanClient` with thin facade over new services

#### Completed Tasks

- [x] **5.1** Create new client module structure
  - Location: `fints/clients/`
  - Base types in `fints/clients/base.py`
  - Clean separation from legacy `fints/client.py`

- [x] **5.2** Implement `FinTS3Client` facade
  - Location: `fints/clients/fints3.py`
  - Uses domain port adapters directly
  - Clean initialization with `ClientCredentials`
  - Context manager for session lifecycle
  - Supports balance, transactions, statements

- [x] **5.3** Implement backward compatibility
  - `FinTS3PinTanClient` lazy-imported with deprecation warning
  - `fints/readonly/` re-exports from `fints/clients/`
  - All existing imports continue to work

- [x] **5.4** Update `ReadOnlyFinTSClient`
  - Moved to `fints/clients/readonly.py`
  - Accepts both `ClientCredentials` and `GatewayCredentials`
  - Backward compatible with existing code

#### Implemented Structure

```
fints/clients/
├── __init__.py        # Public exports: FinTS3Client, ReadOnlyFinTSClient
├── base.py            # ClientCredentials, BankClient protocol
├── fints3.py          # FinTS3Client (new, uses adapters)
└── readonly.py        # ReadOnlyFinTSClient (uses gateway)

fints/readonly/        # Backward compatibility re-exports
├── __init__.py        # Re-exports from fints.clients.readonly
└── client.py          # Re-exports from fints.clients.readonly
```

#### Key Implementation

```python
# fints/client/base.py
from fints.domain import (
    Account, BalanceSnapshot, BankCredentials, BankRoute, TransactionFeed,
)
from fints.domain.ports import (
    AccountDiscoveryPort, BalancePort, SessionPort, TransactionHistoryPort,
)
from fints.infrastructure.fints.adapters import (
    FinTSAccountDiscovery, FinTSBalanceAdapter,
    FinTSSessionAdapter, FinTSTransactionHistory,
)

class FinTS3Client:
    """Modern FinTS 3.0 client using domain-driven architecture."""

    def __init__(
        self,
        credentials: BankCredentials,
        route: BankRoute,
        server_url: str,
        product_id: str,
        product_version: str = "1.0",
        *,
        session_state: SessionToken | None = None,
        challenge_handler: ChallengeHandler | None = None,
    ):
        self._credentials = credentials
        self._route = route
        self._server_url = server_url
        self._product_id = product_id
        self._product_version = product_version
        self._session_state = session_state
        self._challenge_handler = challenge_handler or DefaultChallengeHandler()

        # Initialize infrastructure
        self._dialog_factory = self._create_dialog_factory()

        # Create adapters
        self._session: SessionPort = FinTSSessionAdapter(self._dialog_factory)
        self._accounts: AccountDiscoveryPort = FinTSAccountDiscovery(self._dialog_factory)
        self._balances: BalancePort = FinTSBalanceAdapter(self._dialog_factory)
        self._transactions: TransactionHistoryPort = FinTSTransactionHistory(self._dialog_factory)

    def __enter__(self) -> "FinTS3Client":
        self._state = self._session.open_session(self._credentials, self._session_state)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._state:
            self._session.close_session(self._state)

    def get_accounts(self) -> Sequence[Account]:
        return self._accounts.fetch_accounts(self._state)

    def get_balance(self, account: Account) -> BalanceSnapshot:
        balances = self._balances.fetch_balances(self._state, [account.account_id])
        return balances[0]

    def get_transactions(
        self,
        account: Account,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> TransactionFeed:
        return self._transactions.fetch_history(
            self._state,
            account.account_id,
            start_date,
            end_date,
        )

    @property
    def session_state(self) -> SessionToken | None:
        return self._state
```

---

### Phase 6: Deprecation & Cleanup ✅ COMPLETED

**Duration**: 1-2 weeks (Completed: Nov 28, 2025)
**Priority**: Low
**Goal**: Smooth transition for existing users

#### Completed Tasks

- [x] **6.1** Add deprecation warnings
  - `FinTS3PinTanClient` lazy-imported with deprecation warning from `fints`
  - `fints.readonly` module has note in docstring (no runtime warning to avoid noise)
  - `fints/infrastructure/legacy/tan.py` and `pintan.py` emit deprecation warnings

- [x] **6.2** Clean up obsolete documentation
  - Removed `docs/legacy_refactor_plan.md`
  - Removed `docs/developer/client_refactor_plan.md`
  - Updated references in migration plan

- [x] **6.3** Update example code
  - Updated `examples/read_only_client_demo.py` to use new imports
  - Example shows recommended import pattern from `fints` package

#### Deferred Tasks (for future releases)

- [ ] **6.4** Create migration guide
  - Location: `docs/migration/v4_to_v5.md`
  - Code examples for common patterns
  - Breaking changes list

- [ ] **6.5** Remove legacy code (after deprecation period)
  - Keep `fints/client.py` until adapters are fully standalone
  - Keep `fints/infrastructure/legacy/` components used by client
  - Schedule removal for v5.0

Note: The legacy `FinTS3PinTanClient` is still used internally by the adapters.
Full removal requires replacing the internal implementation with native adapter code,
which is planned for a future release.

---

## Target Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User Code                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Client Layer                              │
│   FinTS3Client (new), ReadOnlyFinTSClient                   │
│   Clean public API, context managers                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Application Layer                           │
│   AccountDiscoveryService, BalanceService, etc.             │
│   GatewayCredentials, BankGateway (protocol)                │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Domain Layer   │ │ Infrastructure  │ │   Future        │
│                 │ │   (FinTS 3.0)   │ │   Adapters      │
│ Models:         │ │                 │ │                 │
│ - Account       │ │ Dialog:         │ │ - PSD2 API      │
│ - Balance       │ │ - Connection    │ │ - EBICS         │
│ - Transaction   │ │ - Transport     │ │ - Mock/Test     │
│ - Payment       │ │ - Responses     │ │                 │
│                 │ │                 │ │                 │
│ Ports:          │ │ Auth:           │ │                 │
│ - SessionPort   │ │ - PIN/TAN       │ │                 │
│ - BalancePort   │ │ - Decoupled     │ │                 │
│ - AccountPort   │ │ - Mechanisms    │ │                 │
│ - etc.          │ │                 │ │                 │
│                 │ │ Adapters:       │ │                 │
│ Connection:     │ │ - Session       │ │                 │
│ - Credentials   │ │ - Accounts      │ │                 │
│ - Challenge     │ │ - Balances      │ │                 │
│ - SessionToken  │ │ - Transactions  │ │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

## Success Criteria

### Phase 1 Complete ✅
- [x] No imports from infrastructure in domain layer
- [x] `SessionToken` protocol defined and used
- [x] All tests pass

### Phase 2 Complete ✅
- [x] Dialog creation extracted from client
- [x] Response processing in dedicated module
- [x] BPD/UPD management separated

### Phase 3 Complete ✅
- [x] Challenge handling via protocol (domain `ChallengeHandler`)
- [x] Decoupled polling reusable (`DecoupledConfirmationPoller`)
- [x] Auth modules created with all components
- [x] TAN workflow independent of client
- [x] Client migrated to new auth imports (via legacy re-exports)
- [x] Legacy modules converted to deprecated re-export wrappers

### Phase 4 Complete ✅
- [x] All domain ports have FinTS implementations
- [x] Adapters importable and instantiable
- [x] Unit tests pass
- [ ] Adapters wired into client (Phase 5)

### Phase 5 Complete ✅
- [x] New `FinTS3Client` API functional
- [x] Legacy `FinTS3PinTanClient` deprecated (lazy import with warning)
- [x] `ReadOnlyFinTSClient` uses new architecture
- [x] Clean public exports from `fints` package

### Phase 6 Complete ✅
- [x] Deprecation warnings added
- [x] Obsolete documentation removed
- [x] Example code updated
- [ ] Migration guide (deferred to v5.0)
- [ ] Legacy code removal (deferred to v5.0)

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking existing users | Maintain backward compatibility shims; long deprecation period |
| Protocol coverage gaps | Keep regression fixtures; test against real banks |
| State migration issues | Provide migration helper for serialized sessions |
| Performance regression | Benchmark critical paths; profile dialog operations |

---

## Timeline Estimate

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1 | 1-2 days | None |
| Phase 2 | 3-5 days | Phase 1 |
| Phase 3 | 3-5 days | Phase 2 |
| Phase 4 | 5-7 days | Phases 2, 3 |
| Phase 5 | 2-3 days | Phase 4 |
| Phase 6 | 1-2 weeks | Phase 5 |

**Total**: ~4-6 weeks

---

## References

- [PRD.md](/PRD.md) - Original read-only refactor PRD

Note: Previous planning documents (`client_refactor_plan.md`, `legacy_refactor_plan.md`)
have been removed as they were superseded by this migration plan.

