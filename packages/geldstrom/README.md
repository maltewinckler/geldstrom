# geldstrom

Pure-Python FinTS 3.0 client for German banking. Handles protocol parsing, dialog management, decoupled TAN (SecureGo+, pushTAN, …), and exposes a synchronous API for reading accounts, balances, and transaction history.

## Package layout

```
geldstrom/
├── clients/
│   ├── base.py               # BankClient protocol
│   ├── fints3.py             # FinTS3Client — blocking, context-manager
│   └── fints3_decoupled.py   # FinTS3ClientDecoupled + PollResult
├── domain/
│   └── model/
│       ├── accounts.py       # Account, AccountOwner, AccountCapabilities
│       ├── balances.py       # BalanceSnapshot, BalanceAmount
│       ├── bank.py           # BankRoute, BankCapabilities, BankCredentials
│       └── transactions.py   # TransactionEntry, TransactionFeed
└── infrastructure/
    └── fints/
        ├── challenge/        # Challenge, ChallengeHandler, TANConfig,
        │                     # DecoupledTANPending, DetachingChallengeHandler
        ├── credentials.py    # GatewayCredentials (FinTS connection bundle)
        ├── dialog/           # Wire-level FinTS dialog (connection, security,
        │                     # message, responses, TAN strategies)
        ├── exceptions.py     # FinTSClientPINError, FinTSConnectionError, …
        ├── operations/       # FinTS operations (accounts, balances,
        │   └── transactions/ # transactions: mt940, camt, feed pipelines)
        ├── protocol/         # Tokenizer, parser, segment/DEG definitions
        ├── services/         # High-level service objects used by clients
        │                     # (FinTSAccountService, FinTSBalanceService,
        │                     #  FinTSTransactionService, FinTSMetadataService)
        ├── session.py        # FinTSSessionState, SessionToken protocol
        ├── support/          # FinTSConnectionHelper, serialization helpers
        └── tan.py            # TANMethod value object
```

## Quick start

```python
from geldstrom import FinTS3Client

with FinTS3Client(
    bank_code="12345678",
    server_url="https://banking.example.com/fints",
    user_id="your_user",
    pin="your_pin",
    product_id="YOUR_PRODUCT_ID",
    tan_method="946",   # required by most banks even for read-only ops
) as client:
    accounts = client.list_accounts()
    balance  = client.get_balance(accounts[0])
    feed     = client.get_transactions(accounts[0])
```

## Clients

### `FinTS3Client`

Standard blocking client. Call `connect()` (or use as a context manager) to open a dialog and discover accounts. Subsequent method calls reuse the cached session. Use `session_state` to persist the session across process restarts.

### `FinTS3ClientDecoupled`

Subclass of `FinTS3Client` that raises `DecoupledTANPending` instead of blocking when the bank requires an app-based confirmation. The live connection context is kept alive internally; call `poll_tan()` in a loop until `status == "approved"`. The gateway uses this variant for all requests.

```python
from geldstrom import FinTS3ClientDecoupled, DecoupledTANPending

client = FinTS3ClientDecoupled(...)
try:
    feed = client.get_transactions(account)
except DecoupledTANPending:
    while True:
        result = client.poll_tan()
        if result.status == "approved":
            feed = result.data
            break
        elif result.status == "pending":
            time.sleep(2)
        else:
            raise RuntimeError(result.error)
```

## TAN handling

Most German banks require a TAN (2FA) even for read-only operations.

- Pass `tan_method` (e.g. `"946"` for SecureGo+/decoupled TAN) to avoid a runtime warning.
- Call `client.get_tan_methods()` to discover all methods advertised by the bank; this performs a lightweight sync dialog that does not require a TAN.
- `TANConfig` controls polling behaviour (`poll_interval`, `timeout_seconds`).
- `ChallengeHandler` is a protocol for custom challenge presentation — the default `DetachingChallengeHandler` raises `DecoupledTANPending` for decoupled challenges.

## Session persistence

`FinTS3Client.session_state` returns a `FinTSSessionState` after `connect()`. Serialize it with `.serialize()` and reconstruct with `FinTSSessionState.deserialize(data)`. Pass the reconstructed state as `session_state=...` to skip the initial sync dialog on subsequent runs.

## Examples

See `examples/` in the repository root for runnable demos (account listing, balance fetching, transaction history, TAN flow walkthrough).
