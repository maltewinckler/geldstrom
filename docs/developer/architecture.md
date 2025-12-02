# Geldstrom Architecture

This document describes the architecture of the geldstrom package, a Python library for accessing German bank accounts via the FinTS/HBCI protocol.

## Overview

Geldstrom follows **Domain-Driven Design (DDD)** principles with a clear separation between domain logic and infrastructure concerns. The architecture is designed for:

1. **Protocol Independence**: The domain layer knows nothing about FinTS specifics
2. **Testability**: Each layer can be tested in isolation
3. **Extensibility**: New protocols (e.g., PSD2/XS2A) can be added without changing the domain
4. **Type Safety**: Pydantic models throughout ensure runtime validation

## Package Structure

```
geldstrom/
├── __init__.py              # Public API exports
├── clients/                 # High-level client implementations
│   ├── base.py              # BankClient protocol
│   └── fints3.py            # FinTS 3.0 implementation
├── domain/                  # Pure domain layer (protocol-agnostic)
│   ├── model/               # Domain entities and value objects
│   ├── ports/               # Abstract interfaces (protocols)
│   └── connection/          # Session and auth abstractions
└── infrastructure/          # Protocol implementations
    └── fints/               # FinTS 3.0 implementation
        ├── adapters/        # Port implementations
        ├── dialog/          # Connection management
        ├── operations/      # Business operations
        └── protocol/        # Wire protocol handling
```

## Architectural Layers

### Layer 1: Client Layer (`geldstrom/clients/`)

The client layer provides the public API that users interact with directly.

```
┌─────────────────────────────────────────────────────────────────┐
│                        BankClient Protocol                       │
│  connect() | disconnect() | list_accounts() | get_balance() ... │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         FinTS3Client                             │
│  Coordinates adapters, manages session lifecycle, context mgr   │
└─────────────────────────────────────────────────────────────────┘
```

**Key Components:**

- **`BankClient`** (Protocol): Defines the contract all clients must satisfy
- **`FinTS3Client`**: Primary implementation for FinTS 3.0 banks

**Design Decisions:**

- Uses Python's `Protocol` for structural typing (duck typing with IDE support)
- Context manager pattern for automatic resource cleanup
- Accepts both `Account` objects and string IDs for flexibility

### Layer 2: Domain Layer (`geldstrom/domain/`)

The domain layer contains pure business logic with no external dependencies. It defines *what* the system does, not *how*.

```
domain/
├── model/                   # Entities & Value Objects
│   ├── accounts.py          # Account, AccountOwner, AccountCapabilities
│   ├── balances.py          # BalanceSnapshot, BalanceAmount
│   ├── transactions.py      # TransactionEntry, TransactionFeed
│   ├── statements.py        # StatementReference, StatementDocument
│   ├── bank.py              # BankRoute, BankCapabilities
│   └── payments.py          # Payment (future use)
├── ports/                   # Abstract Interfaces
│   ├── accounts.py          # AccountDiscoveryPort
│   ├── balances.py          # BalancePort
│   ├── transactions.py      # TransactionHistoryPort
│   ├── statements.py        # StatementPort
│   ├── payments.py          # PaymentPort (future)
│   └── session.py           # SessionPort
└── connection/              # Session Abstractions
    ├── credentials.py       # BankCredentials
    ├── session.py           # SessionToken protocol
    ├── challenge.py         # ChallengeHandler, TAN challenges
    └── retry.py             # Retry policies
```

#### Domain Models

All domain models are **immutable Pydantic models** (`frozen=True`):

```python
class Account(BaseModel, frozen=True):
    """Canonical description of a bank account."""
    account_id: str
    iban: str | None = None
    bic: str | None = None
    currency: str | None = None
    owner: AccountOwner | None = None
    bank_route: BankRoute
    capabilities: AccountCapabilities
```

**Key Properties:**

- **Immutability**: Models cannot be modified after creation
- **Validation**: Pydantic ensures type correctness at runtime
- **Serialization**: Automatic JSON serialization for persistence

#### Ports (Abstract Interfaces)

Ports define contracts that infrastructure must implement:

```python
class AccountDiscoveryPort(Protocol):
    """Retrieve account lists and bank capability metadata."""

    def fetch_bank_capabilities(self, state: SessionToken) -> BankCapabilities:
        ...

    def fetch_accounts(self, state: SessionToken) -> Sequence[Account]:
        ...
```

**Why Ports?**

1. **Decoupling**: Domain doesn't know about FinTS, HTTP, or XML
2. **Testability**: Easily mock infrastructure in unit tests
3. **Extensibility**: Implement new protocols by creating new adapters

### Layer 3: Infrastructure Layer (`geldstrom/infrastructure/`)

The infrastructure layer implements domain ports using specific technologies. Currently, only FinTS 3.0 is implemented.

```
infrastructure/
└── fints/                   # FinTS 3.0 Protocol Implementation
    ├── adapters/            # Domain port implementations
    ├── dialog/              # Connection & session management
    ├── operations/          # FinTS business operations
    └── protocol/            # Wire protocol (parsing/serialization)
```

#### Sub-Layer 3.1: Adapters (`infrastructure/fints/adapters/`)

Adapters implement domain ports by translating between domain models and FinTS operations:

```
adapters/
├── accounts.py              # AccountDiscoveryPort → AccountOperations
├── balances.py              # BalancePort → BalanceOperations
├── transactions.py          # TransactionHistoryPort → TransactionOperations
├── statements.py            # StatementPort → StatementOperations
├── connection.py            # ConnectionHelper (manages Dialog lifecycle)
├── session.py               # Session state management
├── serialization.py         # State serialization helpers
└── helpers.py               # Shared utilities
```

**Example: Balance Adapter**

```python
class FinTSBalanceAdapter:
    """Implements BalancePort using FinTS operations."""

    def fetch_balance(self, account_id: str) -> BalanceSnapshot:
        # 1. Convert account_id to FinTS account identifier
        account = self._find_account(account_id)

        # 2. Execute FinTS operation
        with self._connection_helper.connect(self._state) as ctx:
            ops = BalanceOperations(ctx.dialog, ctx.parameters)
            result = ops.fetch_balance(account)

        # 3. Convert FinTS result to domain model
        return self._balance_from_operations(account_id, result)
```

#### Sub-Layer 3.2: Dialog (`infrastructure/fints/dialog/`)

The dialog layer manages FinTS communication sessions:

```
dialog/
├── connection.py            # HTTPSDialogConnection (HTTP transport)
├── factory.py               # DialogFactory (creates configured dialogs)
├── message.py               # Message building and parsing
├── responses.py             # Response processing
├── security.py              # Authentication & encryption mechanisms
└── logging.py               # Request/response logging
```

**Dialog Lifecycle:**

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Factory    │────▶│   Dialog     │────▶│  Connection  │
│  (config)    │     │  (session)   │     │  (HTTP/TLS)  │
└──────────────┘     └──────────────┘     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  Security    │
                     │  (PIN/TAN)   │
                     └──────────────┘
```

**Key Responsibilities:**

- **DialogFactory**: Creates dialogs with proper configuration
- **Dialog**: Manages message exchange, dialog state, and security
- **SecurityContext**: Handles authentication and encryption
- **HTTPSDialogConnection**: TLS-encrypted HTTP transport

#### Sub-Layer 3.3: Operations (`infrastructure/fints/operations/`)

Operations implement FinTS business transactions using protocol segments:

```
operations/
├── accounts.py              # HKSPA/HISPA (SEPA account discovery)
├── balances.py              # HKSAL/HISAL (balance queries)
├── transactions.py          # HKKAZ/HIKAZ, HKCAZ/HICAZ (transactions)
├── statements.py            # HKEKA/HIEKA (statement downloads)
├── mt940.py                 # MT940/MT942 parsing
├── pagination.py            # Touch-ahead pagination
├── enums.py                 # FinTS operation codes
└── helpers.py               # Segment version selection
```

**Operation Pattern:**

```python
class BalanceOperations:
    """Fetches account balances via HKSAL/HISAL."""

    def fetch_balance(self, account: SEPAAccount) -> BalanceResult:
        # 1. Build request segment
        segment = self._build_hksal_segment(account)

        # 2. Send via dialog
        response = self._dialog.send(segment)

        # 3. Extract result from response
        return self._parse_hisal_response(response)
```

#### Sub-Layer 3.4: Protocol (`infrastructure/fints/protocol/`)

The protocol layer handles FinTS wire format encoding/decoding:

```
protocol/
├── base.py                  # FinTSSegment, FinTSDataElementGroup base classes
├── parser.py                # FinTSParser (bytes → segments)
├── tokenizer.py             # Low-level tokenization
├── types.py                 # Custom Pydantic types (FinTSNumeric, FinTSDate, ...)
├── parameters.py            # BPD/UPD parameter stores
├── formals/                 # Data Element Groups (DEGs)
│   ├── identifiers.py       # BankIdentifier, AccountIdentifier
│   ├── amounts.py           # Amount, Balance
│   ├── security.py          # SecurityProfile, KeyName
│   ├── responses.py         # Response codes
│   ├── tan.py               # TAN media, challenge data
│   └── ...
└── segments/                # Segment definitions
    ├── accounts.py          # HKSPA, HISPA
    ├── saldo.py             # HKSAL, HISAL
    ├── transactions.py      # HKKAZ, HIKAZ, HKCAZ, HICAZ
    ├── dialog.py            # HNHBK, HNHBS (message framing)
    ├── message.py           # HNVSK, HNVSD (encryption)
    ├── auth.py              # HKIDN, HKVVB (identification)
    ├── pintan.py            # HKTAN, HITAN, HITANS
    └── ...
```

**Segment Definition Pattern:**

```python
class HKSAL7(FinTSSegment, segment_type="HKSAL", version=7):
    """Balance request segment (version 7)."""

    account: AccountInternational = Field(description="Target account")
    all_accounts: bool = Field(default=False)
    max_entries: int | None = Field(default=None)
    continuation_id: str | None = Field(default=None)
```

**Parser Architecture:**

```
Raw Bytes
    │
    ▼
┌──────────────────┐
│    Tokenizer     │  Split by @ and + delimiters
└──────────────────┘
    │
    ▼
┌──────────────────┐
│  Segment Parser  │  Match segment type and version
└──────────────────┘
    │
    ▼
┌──────────────────┐
│  Pydantic Model  │  Validate and construct typed segment
└──────────────────┘
```

## Data Flow

### Request Flow (User → Bank)

```
User Code
    │
    │ client.get_balance("account-123")
    ▼
┌─────────────────────────────────────────────────────────────────┐
│                       FinTS3Client                               │
│  1. Resolve account ID to Account object                         │
│  2. Delegate to FinTSBalanceAdapter                              │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FinTSBalanceAdapter                           │
│  3. Convert Account → SEPAAccount                                │
│  4. Create BalanceOperations with active dialog                  │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BalanceOperations                             │
│  5. Build HKSAL segment                                          │
│  6. Call dialog.send(segment)                                    │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Dialog                                   │
│  7. Wrap in message envelope (HNHBK, HNHBS)                      │
│  8. Apply encryption (HNVSK, HNVSD)                              │
│  9. Serialize to bytes                                           │
│  10. Send via HTTPSDialogConnection                              │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│                  HTTPSDialogConnection                           │
│  11. POST to bank URL with TLS                                   │
│  12. Receive response bytes                                      │
└─────────────────────────────────────────────────────────────────┘
```

### Response Flow (Bank → User)

```
Response Bytes
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│                       FinTSParser                                │
│  1. Tokenize message                                             │
│  2. Parse segments by type/version                               │
│  3. Construct Pydantic segment objects                           │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BalanceOperations                             │
│  4. Find HISAL segment in response                               │
│  5. Extract balance data                                         │
│  6. Return BalanceResult                                         │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FinTSBalanceAdapter                           │
│  7. Convert BalanceResult → BalanceSnapshot (domain model)       │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│                       FinTS3Client                               │
│  8. Return BalanceSnapshot to user                               │
└─────────────────────────────────────────────────────────────────┘
```

## Two-Factor Authentication (TAN)

German banks require TAN (Transaction Authentication Number) for sensitive operations.

### Decoupled TAN Flow

```
┌────────────┐      ┌────────────┐      ┌────────────┐
│   Client   │      │    Bank    │      │  User App  │
└─────┬──────┘      └─────┬──────┘      └─────┬──────┘
      │                   │                   │
      │  HKSAL (request)  │                   │
      │──────────────────▶│                   │
      │                   │                   │
      │  HITAN (pending)  │  Push notify      │
      │◀──────────────────│──────────────────▶│
      │                   │                   │
      │  HKTAN (poll)     │                   │
      │──────────────────▶│                   │
      │                   │   ◀─ User approves│
      │  HITAN (approved) │                   │
      │◀──────────────────│                   │
      │                   │                   │
      │  HISAL (result)   │                   │
      │◀──────────────────│                   │
```

**Implementation:**

1. **ChallengeHandler**: User-provided callback for TAN input
2. **Decoupled Polling**: Automatic background polling for app-based TAN
3. **Timeout Handling**: Configurable polling interval and max duration

## Session Management

Sessions maintain state between operations:

```python
@dataclass
class FinTSSessionState:
    """Serializable session state."""

    route: BankRoute           # Bank identifier
    user_id: str               # FinTS user ID
    system_id: str             # Assigned system ID
    bpd_blob: bytes            # Bank Parameter Data (compressed)
    upd_blob: bytes            # User Parameter Data (compressed)
    bpd_version: int           # BPD version number
    upd_version: int           # UPD version number
    created_at: datetime       # Session creation time
```

**Session State Contents:**

- **System ID**: Unique identifier assigned by bank
- **BPD (Bank Parameter Data)**: Supported operations, limits, formats
- **UPD (User Parameter Data)**: User's accounts, permissions

**Benefits of Session Reuse:**

- Skip parameter negotiation (faster connection)
- Preserve system ID (avoid re-registration)
- Note: Does NOT bypass TAN requirements

## Extensibility

### Adding a New Protocol (e.g., PSD2/XS2A)

The architecture supports adding alternative protocols:

```
infrastructure/
├── fints/                   # Existing FinTS implementation
│   └── adapters/
│       ├── accounts.py      # FinTSAccountDiscovery
│       └── ...
│
└── xs2a/                    # Future PSD2 implementation
    └── adapters/
        ├── accounts.py      # XS2AAccountDiscovery
        └── ...
```

**Steps:**

1. Create new `infrastructure/xs2a/` directory
2. Implement domain ports in `xs2a/adapters/`
3. Create new client in `clients/xs2a.py`
4. No changes to domain layer required

### Adding New Operations

To add a new banking operation:

1. **Domain Model** (`domain/model/`): Define result type
2. **Port** (`domain/ports/`): Define abstract interface
3. **Operation** (`infrastructure/fints/operations/`): Implement FinTS exchange
4. **Adapter** (`infrastructure/fints/adapters/`): Bridge port to operation
5. **Client** (`clients/fints3.py`): Expose method to users

### Adding Segment Support

To support a new FinTS segment:

1. **Define DEGs** (`protocol/formals/`): Create data element groups
2. **Define Segment** (`protocol/segments/`): Create segment class
3. **Auto-Registration**: Segment is automatically registered via `__init_subclass__`

```python
class HKNEW1(FinTSSegment, segment_type="HKNEW", version=1):
    """New segment definition."""
    field: str = Field(description="Example field")

# Automatically registered - can now be parsed!
```

## Error Handling

### Error Hierarchy

```
FinTSError (base)
├── FinTSConnectionError      # Network/transport errors
├── FinTSAuthenticationError  # PIN/TAN errors
├── FinTSParserError          # Protocol parsing errors
└── FinTSOperationError       # Business operation failures
```

### Robust Parsing Mode

The parser operates in "hybrid" mode:

- **Known segments**: Strict parsing with validation
- **Unknown segments**: Log warning, create generic segment
- **Parse errors**: Log warning, continue with partial data

This ensures compatibility with bank-specific extensions.

## Testing Strategy

```
tests/
├── fixtures/                # Test data
├── unit/                    # Isolated component tests
│   ├── clients/             # Client tests (mocked adapters)
│   ├── domain/              # Domain model tests
│   └── infrastructure/
│       └── fints/
│           ├── adapters/    # Adapter tests (mocked ops)
│           ├── dialog/      # Dialog tests (mocked HTTP)
│           ├── operations/  # Operation tests (mocked dialog)
│           └── protocol/    # Parser/serializer tests
└── integration/             # End-to-end tests (real bank)
```

**Testing Guidelines:**

- **Unit tests**: Mock dependencies, test in isolation
- **Integration tests**: Real bank connections, requires credentials
- **Fixture data**: Sample FinTS messages for parser tests

## Configuration

### Required Settings

| Setting | Description |
|---------|-------------|
| `bank_code` | 8-digit German bank routing code (BLZ) |
| `server_url` | Bank's FinTS endpoint URL |
| `user_id` | FinTS login username |
| `pin` | FinTS password |
| `product_id` | Registered software product ID |

### Optional Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `country_code` | `"DE"` | ISO country code |
| `customer_id` | `user_id` | Customer identifier (if different) |
| `tan_method` | Auto | TAN method code (e.g., "920") |
| `tan_medium` | None | TAN medium name (e.g., "Mein Handy") |
| `product_version` | `"1.0"` | Software version string |

## Performance Considerations

### Connection Pooling

Currently, each operation creates a new dialog. Future optimization:

```python
# Potential future API
async with client.session() as session:
    balance = await session.get_balance(account)
    transactions = await session.get_transactions(account)
```

### Caching

BPD/UPD parameters are cached in session state:

- Parameters valid for ~24 hours typically
- Version numbers checked on connection
- Automatic refresh when bank indicates new version

## Security

### Transport Security

- TLS 1.2+ required for all connections
- Certificate validation enforced
- No plaintext credential storage

### Credential Handling

- PIN stored in memory only during session
- Session state excludes PIN (only contains signed system ID)
- TAN never stored (single-use by design)

### Audit Logging

- All request/response exchanges logged at DEBUG level
- Sensitive data (PIN, TAN) redacted from logs
- Request IDs for correlation

