# Geldstrom Architecture

This document describes the architecture of the `geldstrom` package — a pure-Python FinTS 3.0 client for German online banking.

## Overview

`geldstrom` follows Domain-Driven Design with a strict layered structure. The domain layer holds only value objects and is free of any protocol knowledge. All FinTS-specific logic lives in the infrastructure layer.

Design goals:
- **Protocol independence** — the domain layer knows nothing about FinTS
- **Testability** — each layer can be tested in isolation
- **Type safety** — all public-facing types are immutable Pydantic models or frozen dataclasses

## Package structure

```
geldstrom/
├── __init__.py                    Public API surface
├── clients/
│   ├── base.py                    BankClient protocol (structural typing)
│   ├── fints3.py                  FinTS3Client — synchronous, context-manager
│   └── fints3_decoupled.py        FinTS3ClientDecoupled + PollResult
├── domain/
│   └── model/
│       ├── accounts.py            Account, AccountOwner, AccountCapabilities
│       ├── balances.py            BalanceSnapshot, BalanceAmount
│       ├── bank.py                BankRoute, BankCapabilities, BankCredentials
│       └── transactions.py        TransactionEntry, TransactionFeed
└── infrastructure/
    └── fints/
        ├── challenge/
        │   ├── types.py           Challenge (ABC), ChallengeData, ChallengeResult,
        │   │                      ChallengeType
        │   ├── handlers.py        ChallengeHandler protocol, DetachingChallengeHandler
        │   └── polling.py         TANConfig, DecoupledTANPending
        ├── credentials.py         GatewayCredentials (FinTS connection bundle)
        ├── debug.py               Debug helpers
        ├── dialog/
        │   ├── connection.py      HTTPSDialogConnection (HTTP/TLS transport)
        │   ├── core.py            FinTSDialog — message exchange, session state
        │   ├── challenge.py       FinTSChallenge — wraps HITAN for domain interface
        │   ├── logging.py         Request/response debug logging
        │   ├── message.py         Message building, encryption envelope
        │   ├── responses.py       Response parsing helpers
        │   ├── security.py        PIN/TAN authentication, encryption
        │   └── tan_strategies/    Blocking, decoupled, no-TAN strategies
        ├── exceptions.py          FinTSClientPINError, FinTSConnectionError, …
        ├── operations/
        │   ├── accounts.py        AccountOperations (HKSPA/HISPA → AccountInfo)
        │   ├── balances.py        BalanceOperations (HKSAL/HISAL → BalanceResult)
        │   ├── enums.py           FinTS segment version enums
        │   ├── helpers.py         Segment version selection
        │   ├── pagination.py      Touch-ahead pagination
        │   └── transactions/
        │       ├── mt940.py       Mt940Fetcher (HKKAZ/HIKAZ → TransactionFeed)
        │       ├── camt.py        CamtFetcher (HKCAZ/HICAZ → TransactionFeed)
        │       └── feed.py        Shared feed-building utilities
        ├── protocol/
        │   ├── base.py            FinTSSegment, DataElement base classes
        │   ├── parser.py          FinTSParser (bytes → typed segments)
        │   ├── tokenizer.py       Low-level byte tokenizer
        │   ├── types.py           Custom Pydantic types (FinTSDate, FinTSNumeric, …)
        │   ├── parameters.py      ParameterStore, BPD/UPD data access
        │   ├── formals/           Data Element Groups (DEGs):
        │   │                      amounts, enums, identifiers, parameters,
        │   │                      responses, security, tan, transactions
        │   └── segments/          Typed segment definitions:
        │                          accounts (HKSPA/HISPA), auth (HKIDN/HKVVB),
        │                          bank (HKABI), dialog (HNHBK/HNHBS),
        │                          message (HNVSK/HNVSD), params (BPD/UPD),
        │                          pintan (HKTAN/HITAN/HITANS),
        │                          saldo (HKSAL/HISAL),
        │                          transactions (HKKAZ/HIKAZ/HKCAZ/HICAZ)
        ├── services/
        │   ├── base.py            FinTSServiceBase — credential/config injection
        │   ├── accounts.py        FinTSAccountService → AccountDiscoveryResult
        │   ├── balances.py        FinTSBalanceService → BalanceSnapshot(s)
        │   ├── metadata.py        FinTSMetadataService → TANMethod list
        │   └── transactions.py    FinTSTransactionService → TransactionFeed
        ├── session.py             FinTSSessionState (frozen dataclass), SessionToken protocol
        ├── support/
        │   ├── connection.py      FinTSConnectionHelper, ConnectionContext
        │   ├── helpers.py         locate_sepa_account, account_key
        │   └── serialization.py   Session state serialization helpers
        └── tan.py                 TANMethod value object
```

---

## Layers

### Layer 1 — Client (`clients/`)

Entry point for application code. `FinTS3Client` is the standard blocking client. `FinTS3ClientDecoupled` is the subclass used by the gateway: instead of blocking on a TAN challenge it raises `DecoupledTANPending` immediately, allowing the caller to resume later.

```
BankClient (Protocol)
    │
    ├── FinTS3Client
    │       • connect() → Sequence[Account]
    │       • list_accounts(), get_account()
    │       • get_balance(), get_balances()
    │       • get_transactions()
    │       • get_tan_methods()
    │       • session_state, capabilities, is_connected, tan_config
    │
    └── FinTS3ClientDecoupled (subclass)
            • Overrides operations that can trigger TAN
            • Raises DecoupledTANPending instead of blocking
            • poll_tan() → PollResult
            • cleanup_pending()
```

Key design choice: both clients delegate all FinTS work to service objects in `infrastructure/fints/services/` and never reach into the protocol layer directly.

### Layer 2 — Domain (`domain/`)

Pure value objects with no external dependencies. All models are `frozen=True` Pydantic models — immutable after construction.

```
domain/model/
├── BankRoute          country_code + bank_code (e.g. DE-12345678)
├── BankCapabilities   frozenset of supported FinTS operations
├── BankCredentials    user_id, secret (SecretStr), customer_id, 2FA config
├── Account            account_id, iban, bic, currency, owner, bank_route,
│                      capabilities, product_name
├── AccountOwner       name, address
├── AccountCapabilities  can_fetch_balance, can_list_transactions, …
├── BalanceSnapshot    account_id, as_of, booked, pending, available, credit_limit
├── BalanceAmount      amount (Decimal), currency
├── TransactionFeed    account_id, entries, start_date, end_date, has_more
└── TransactionEntry   entry_id, booking_date, value_date, amount, currency,
                       purpose, counterpart_name, counterpart_iban
```

### Layer 3 — Infrastructure (`infrastructure/fints/`)

Everything FinTS-specific lives here. The layer is further divided into logical sub-layers.

#### 3a — Services (`services/`)

Service objects are the integration point between the client layer and the FinTS internals. Each service owns one responsibility:

| Service | Responsibility |
|---------|---------------|
| `FinTSAccountService` | Open a dialog, run `AccountOperations`, map results to domain types |
| `FinTSBalanceService` | Open a dialog, run `BalanceOperations`, map to `BalanceSnapshot` |
| `FinTSTransactionService` | Orchestrate `Mt940Fetcher` / `CamtFetcher`, fall back between formats |
| `FinTSMetadataService` | Extract TAN methods from BPD; performs a sync dialog if no cached state |

All services extend `FinTSServiceBase` which handles credential/config injection and `FinTSConnectionHelper` construction.

#### 3b — Connection support (`support/`)

`FinTSConnectionHelper` manages the dialog lifecycle (open → authenticate → yield `ConnectionContext` → close). `ConnectionContext` is a context manager that holds the active `FinTSDialog` and `ParameterStore` needed by operations and services.

```python
with helper.connect(session_state) as ctx:
    ops = BalanceOperations(ctx.dialog, ctx.parameters)
    result = ops.fetch_balance(sepa_account)
```

#### 3c — Challenge handling (`challenge/`)

The `challenge/` package is intentionally isolated from the dialog code so that TAN handling logic can be tested without a live connection.

```
Challenge (ABC)           protocol-agnostic 2FA challenge
ChallengeData             binary payload for visual challenges (photoTAN, flicker)
ChallengeType             DECOUPLED | TEXT
ChallengeHandler          Protocol: present_challenge(challenge) → ChallengeResult
DetachingChallengeHandler default handler; returns detach=True for decoupled challenges
TANConfig                 poll_interval + timeout_seconds
DecoupledTANPending       exception raised when TAN confirmation is deferred to caller
```

`DecoupledTANPending` carries the live `ConnectionContext` (dialog kept open) and the `task_reference` needed to resume polling — that is what `FinTS3ClientDecoupled` stores while the gateway's background worker polls.

#### 3d — Operations (`operations/`)

Operations are thin wrappers that send a specific FinTS segment pair (request/response) and return typed results. They receive an already-open dialog and a parameter store; they never open connections themselves.

```
AccountOperations     HKSPA → HISPA  (list SEPA accounts + UPD metadata)
BalanceOperations     HKSAL → HISAL  (booked/pending/available/limit)
Mt940Fetcher          HKKAZ → HIKAZ  (MT940 transaction history)
CamtFetcher           HKCAZ → HICAZ  (CAMT.052/053 transaction history)
```

`FinTSTransactionService` picks `Mt940Fetcher` by default and falls back to `CamtFetcher` on `FinTSUnsupportedOperation`; when `include_pending=True` is requested it tries `CamtFetcher` first.

#### 3e — Dialog (`dialog/`)

The dialog manages the raw FinTS protocol session: message numbering, encryption, signature, and TAN strategy execution. It is driven by the connection helper; external code should not instantiate dialogs directly.

TAN strategies are pluggable:
- `no_tan.py` — anonymous sync dialog (only used by metadata service)
- `base.py` — standard blocking decoupled TAN
- `decoupled.py` — detaching strategy used by `FinTS3ClientDecoupled`

#### 3f — Protocol (`protocol/`)

Pure parsing and serialization. No network, no business logic.

```
Tokenizer → Parser → Pydantic segment models
   bytes      bytes     typed Python objects
```

`ParameterStore` wraps parsed BPD/UPD data and provides convenience accessors (e.g. `get_supported_operations()`, `get_max_segment_version()`).

#### 3g — Session (`session.py`)

`FinTSSessionState` is a frozen dataclass implementing the `SessionToken` protocol. It stores enough data to resume a dialog without a new synchronization round-trip:

| Field | Description |
|-------|-------------|
| `route` | `BankRoute` identifying the bank |
| `user_id` | FinTS user identifier |
| `system_id` | System ID assigned by bank during first sync |
| `client_blob` | Compressed serialized BPD + UPD + dialog client state |
| `bpd_version` | BPD version number |
| `upd_version` | UPD version number |
| `created_at` | ISO 8601 timestamp of session creation |

Call `.serialize()` to get UTF-8 JSON bytes; reconstruct with `FinTSSessionState.deserialize(data)`.

---

## Data flow — balance request

```
client.get_balance(account)
        │
        ▼
FinTS3Client
  • look up Account in cached list
  • delegate to FinTSBalanceService
        │
        ▼
FinTSBalanceService
  • creates FinTSConnectionHelper
  • opens ConnectionContext (dialog + parameters)
        │
        ▼
FinTSConnectionHelper
  • builds FinTSDialog with GatewayCredentials + TANConfig + ChallengeHandler
  • sends HKIDN / HKVVB identification
  • sends HKSYN synchronization (skipped if session_state provided)
        │
        ▼
BalanceOperations
  • resolves SEPAAccount from account_id
  • builds HKSAL segment
  • calls dialog.send(segment)
        │
        ▼
FinTSDialog
  • wraps segment in HNHBK/HNHBS message envelope
  • applies HNVSK/HNVSD encryption
  • serializes to wire bytes
  • POSTs to bank PIN/TAN URL via HTTPSDialogConnection
  • parses response bytes → typed segment objects
  • if HITAN(3920) returned → invokes TAN strategy
        │
        ▼
FinTSBalanceService
  • extracts HISAL segment
  • maps to BalanceSnapshot (domain model)
        │
        ▼
FinTS3Client.get_balance() returns BalanceSnapshot
```

---

## Decoupled TAN flow (gateway path)

```
gateway: FetchTransactionsCommand
        │
        ▼
FinTS3ClientDecoupled.get_transactions()
        │  raises DecoupledTANPending (dialog kept open, task_reference captured)
        │
        ▼
GeldstromBankingConnector
  • catches DecoupledTANPending
  • serializes dialog state into DecoupledSessionSnapshot (bytes)
  • stores snapshot in RedisOperationSessionStore (TTL-based)
  • returns 202 with operation_id to HTTP caller
        │
[client polls: POST /v1/banking/operations/{id}/poll]
        │
        ▼
PollOperationCommand
  • loads DecoupledSessionSnapshot from Redis
  • reconstructs FinTS3ClientDecoupled from snapshot
  • calls FinTS3ClientDecoupled.poll_tan()
  │   • PollResult.status == "pending" → re-serialize, update store, return 202
  │   • PollResult.status == "approved" → store result, session = completed, return 200
  └─  • PollResult.status == "failed" / "expired" → session = failed, return 200
```

---

## Session persistence (gateway path)

When the gateway receives a banking request it:

1. Builds `GatewayCredentials` from the request body and the loaded product key.
2. Constructs a `FinTS3ClientDecoupled` (no session state for the first request).
3. After a successful response, the client's `session_state` is populated — but **not** persisted between independent HTTP requests (each request opens a fresh dialog).
4. For **pending TAN sessions**, the full dialog state is serialized into a `DecoupledSessionSnapshot` and stored in Redis (with a TTL). Subsequent `poll` requests deserialize the snapshot, resume the dialog, and re-serialize the updated state.

---

## Extending the protocol

Adding a new banking operation (e.g. scheduled-payment queries):

1. **Domain model** (`domain/model/`): add the result value object.
2. **Operation** (`infrastructure/fints/operations/`): implement the segment pair.
3. **Service** (`infrastructure/fints/services/`): add a method or new service class.
4. **Client** (`clients/fints3.py`): add a public method delegating to the service.
5. **`__init__.py`**: export the new type if needed.

No changes to the dialog or protocol layers are required.
