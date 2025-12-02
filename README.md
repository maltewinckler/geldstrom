# Geldstrom

Access your German bank accounts programmatically. Geldstrom is a Python client for FinTS 3.0, the standardized banking protocol used by Sparkassen, Volksbanken, Deutsche Bank, DKB, and most other German financial institutions.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: BUSL 1.1](https://img.shields.io/badge/License-BUSL%201.1-blue.svg)](https://mariadb.com/bsl11/)

## Features

- **Account access** — List accounts, fetch balances, download transaction history
- **Modern TAN support** — Decoupled authentication via SecureGo, pushTAN, and similar app-based methods
- **Multiple formats** — Parses both legacy MT940 and modern CAMT.052/053 transaction data
- **Type-safe** — Pydantic models with full validation throughout
- **Read-only** — Designed for data retrieval, not transfers (safe by default)

## Installation

```bash
pip install geldstrom
```

Or with Poetry:

```bash
poetry add geldstrom
```

## Quick Start

```python
from geldstrom import FinTS3Client

with FinTS3Client(
    bank_code="12345678",
    server_url="https://banking.example.com/fints",
    user_id="your_username",
    pin="your_pin",
    product_id="YOUR_PRODUCT_ID",
) as client:
    # List accounts
    for account in client.list_accounts():
        print(f"{account.iban} ({account.currency})")

    # Get balance
    balance = client.get_balance(account)
    print(f"Balance: {balance.booked.amount} {balance.booked.currency}")

    # Fetch transactions
    transactions = client.get_transactions(account)
    for tx in transactions.entries:
        print(f"{tx.booking_date}: {tx.amount} {tx.currency} - {tx.purpose}")
```

**Note:** The `product_id` requires registration with the [Deutsche Kreditwirtschaft](https://www.die-dk.de/) (German Banking Industry Committee). Register at [fints.org](https://www.fints.org/de/hersteller/produktregistrierung)). It is for free and usually, they respond rather quickly (think weeks, not months).

## API Reference

### FinTS3Client

The main client class for interacting with banks.

#### Constructor

```python
from geldstrom import FinTS3Client, TANConfig

FinTS3Client(
    bank_code: str,           # Bank identifier (BLZ), e.g., "12345678"
    server_url: str,          # FinTS server URL
    user_id: str,             # Online banking username
    pin: str,                 # Online banking PIN
    product_id: str,          # FinTS product registration ID
    *,
    country_code: str = "DE", # Country code (default: Germany)
    customer_id: str = None,  # Customer ID if different from user_id
    tan_medium: str = None,   # TAN device name (e.g., "SecureGo")
    tan_method: str = None,   # TAN method identifier (usually auto-detected)
    tan_config: TANConfig = None,  # TAN polling configuration
)
```

#### Methods

| Method | Description | Returns |
|--------|-------------|---------|
| `connect()` | Establish connection and fetch accounts | `Sequence[Account]` |
| `disconnect()` | Close the session | `None` |
| `list_accounts()` | List all accessible accounts | `Sequence[Account]` |
| `get_account(account_id)` | Get account by ID | `Account` |
| `get_balance(account)` | Fetch current balance | `BalanceSnapshot` |
| `get_balances(account_ids)` | Fetch multiple balances | `Sequence[BalanceSnapshot]` |
| `get_transactions(account, start_date, end_date)` | Fetch transaction history | `TransactionFeed` |

#### Properties

| Property | Description | Type |
|----------|-------------|------|
| `is_connected` | Connection status | `bool` |
| `capabilities` | Bank's advertised capabilities | `BankCapabilities` |
| `session_state` | Current session for persistence | `SessionToken` |
| `tan_config` | TAN polling configuration | `TANConfig` |

#### Context Manager

The client supports the context manager protocol:

```python
with FinTS3Client(...) as client:
    # client.connect() called automatically
    accounts = client.list_accounts()
# client.disconnect() called automatically
```

### Data Models

#### Account

Represents a bank account.

| Field | Type | Description |
|-------|------|-------------|
| `account_id` | `str` | Unique identifier (format: `account_number:subaccount`) |
| `iban` | `str` | IBAN |
| `bic` | `str` | BIC/SWIFT code |
| `currency` | `str` | Account currency (e.g., "EUR") |
| `owner` | `AccountOwner` | Account owner information |
| `capabilities` | `AccountCapabilities` | What operations are supported |

#### BalanceSnapshot

Current account balance.

| Field | Type | Description |
|-------|------|-------------|
| `account_id` | `str` | Account identifier |
| `booked` | `BalanceAmount` | Booked (confirmed) balance |
| `pending` | `BalanceAmount \| None` | Pending (unconfirmed) balance |
| `available` | `BalanceAmount \| None` | Available balance (may differ due to holds) |
| `credit_limit` | `BalanceAmount \| None` | Credit limit on the account |
| `as_of` | `datetime` | Timestamp of the balance |

#### TransactionFeed

Collection of transactions.

| Field | Type | Description |
|-------|------|-------------|
| `account_id` | `str` | Account identifier |
| `start_date` | `date` | Start of date range |
| `end_date` | `date` | End of date range |
| `entries` | `list[TransactionEntry]` | Transaction entries |
| `has_more` | `bool` | Whether more transactions are available (pagination) |

#### TransactionEntry

A single transaction.

| Field | Type | Description |
|-------|------|-------------|
| `entry_id` | `str` | Unique transaction identifier |
| `amount` | `Decimal` | Transaction amount (negative for debits) |
| `currency` | `str` | Currency code |
| `booking_date` | `date` | Date booked |
| `value_date` | `date` | Value date |
| `purpose` | `str` | Transaction purpose/description |
| `counterpart_name` | `str` | Name of counterparty |
| `counterpart_iban` | `str` | IBAN of counterparty |

## Examples

### List All Accounts

Connect to your bank and enumerate all available accounts:

```python
from geldstrom import FinTS3Client

with FinTS3Client(
    bank_code="12345678",
    server_url="https://banking.example.com/fints",
    user_id="your_username",
    pin="your_pin",
    product_id="YOUR_PRODUCT_ID",
) as client:
    for account in client.list_accounts():
        print(f"ID:       {account.account_id}")
        print(f"IBAN:     {account.iban}")
        print(f"BIC:      {account.bic}")
        print(f"Currency: {account.currency}")
        print(f"Owner:    {account.owner.name}")
        print()
```

### Get a Specific Account

Retrieve an account by its ID (format: `account_number:subaccount`):

```python
with FinTS3Client(...) as client:
    # Get by account ID
    account = client.get_account("1234567890:0")

    # Check what operations are supported
    print(f"Can fetch balance: {account.capabilities.can_fetch_balance}")
    print(f"Can list transactions: {account.capabilities.can_list_transactions}")
```

### Fetch Balance for One Account

```python
with FinTS3Client(...) as client:
    account = client.get_account("1234567890:0")
    balance = client.get_balance(account)

    print(f"Booked:    {balance.booked.amount:,.2f} {balance.booked.currency}")
    if balance.available:
        print(f"Available: {balance.available.amount:,.2f} {balance.available.currency}")
    print(f"As of:     {balance.as_of}")
```

### Fetch Balances for All Accounts

Use `get_balances()` to efficiently fetch balances for multiple accounts:

```python
with FinTS3Client(...) as client:
    balances = client.get_balances()  # All accounts

    total = sum(float(b.booked.amount) for b in balances)

    for balance in balances:
        print(f"{balance.account_id}: {balance.booked.amount:,.2f} EUR")

    print(f"Total: {total:,.2f} EUR")
```

### Fetch Transaction History

Retrieve transactions with optional date filtering:

```python
from datetime import date, timedelta

with FinTS3Client(...) as client:
    account = client.list_accounts()[0]

    # Last 30 days
    feed = client.get_transactions(
        account,
        start_date=date.today() - timedelta(days=30),
        end_date=date.today(),
    )

    print(f"Found {len(feed.entries)} transactions")

    for tx in feed.entries:
        sign = "+" if tx.amount >= 0 else ""
        print(f"{tx.booking_date} | {sign}{tx.amount:,.2f} {tx.currency}")
        print(f"  {tx.counterpart_name or 'Unknown'}")
        print(f"  {tx.purpose[:60]}...")
```

### Calculate Income and Expenses

```python
from datetime import date, timedelta

with FinTS3Client(...) as client:
    feed = client.get_transactions(
        client.list_accounts()[0],
        start_date=date.today() - timedelta(days=30),
    )

    income = sum(float(tx.amount) for tx in feed.entries if tx.amount > 0)
    expenses = sum(float(tx.amount) for tx in feed.entries if tx.amount < 0)

    print(f"Income:   +{income:,.2f} EUR")
    print(f"Expenses: {expenses:,.2f} EUR")
    print(f"Net:      {income + expenses:,.2f} EUR")
```

### Session Persistence

Save and restore session state to speed up subsequent connections:

```python
import json
from pathlib import Path
from geldstrom import FinTS3Client
from geldstrom.infrastructure.fints import FinTSSessionState

SESSION_FILE = Path(".session_state.json")

def load_session() -> FinTSSessionState | None:
    if not SESSION_FILE.exists():
        return None
    return FinTSSessionState.from_dict(json.loads(SESSION_FILE.read_text()))

def save_session(state):
    if isinstance(state, FinTSSessionState):
        SESSION_FILE.write_text(json.dumps(state.to_dict(), indent=2))

# First connection - fresh
with FinTS3Client(...) as client:
    accounts = client.list_accounts()
    save_session(client.session_state)

# Later connections - faster (skips parameter sync)
with FinTS3Client(..., session_state=load_session()) as client:
    balance = client.get_balance(client.list_accounts()[0])
```

> **Note:** Session persistence speeds up connection by caching bank parameters (BPD/UPD) and system ID. It does **not** bypass 2FA/TAN authentication—German banks require fresh authentication for each session.

### Using Environment Variables

For cleaner code, load credentials from environment variables:

```python
import os
from geldstrom import FinTS3Client

client = FinTS3Client(
    bank_code=os.environ["FINTS_BLZ"],
    server_url=os.environ["FINTS_SERVER"],
    user_id=os.environ["FINTS_USER"],
    pin=os.environ["FINTS_PIN"],
    product_id=os.environ["FINTS_PRODUCT_ID"],
    tan_medium=os.environ.get("FINTS_TAN_MEDIUM"),  # Optional
)
```

See the `examples/` directory for complete, runnable scripts.

## TAN Handling

Geldstrom supports decoupled TAN methods (SecureGo, pushTAN). When a TAN is required:

1. You receive a push notification in your banking app
2. Approve the request in the app
3. The client automatically polls for confirmation and continues

```python
from datetime import date, timedelta

# Fetching older transactions typically requires TAN approval
transactions = client.get_transactions(
    account,
    start_date=date.today() - timedelta(days=90),
    end_date=date.today(),
)
```

### Configuring TAN Polling

You can customize the polling behavior with `TANConfig`:

```python
from geldstrom import FinTS3Client, TANConfig

# Custom TAN configuration
tan_config = TANConfig(
    poll_interval=3.0,      # Poll every 3 seconds (default: 2.0)
    timeout_seconds=180.0,  # Wait up to 3 minutes (default: 120.0)
)

client = FinTS3Client(
    bank_code="12345678",
    server_url="https://banking.example.com/fints",
    user_id="your_username",
    pin="your_pin",
    product_id="YOUR_PRODUCT_ID",
    tan_config=tan_config,
)

# Or update after creation
client.tan_config = TANConfig(poll_interval=5.0, timeout_seconds=300.0)
```

### Custom Challenge Handler

For advanced use cases, you can provide a custom challenge handler:

```python
from geldstrom.domain import ChallengeHandler, Challenge, ChallengeResult

class MyChallengeHandler:
    def present_challenge(self, challenge: Challenge) -> ChallengeResult:
        print(f"Please confirm: {challenge.challenge_text}")
        # For decoupled TAN, return empty result to trigger polling
        return ChallengeResult()

client = FinTS3Client(
    ...,
    challenge_handler=MyChallengeHandler(),
)
```

## Configuration

### Environment Variables

```bash
FINTS_BLZ=12345678
FINTS_COUNTRY=DE
FINTS_USER=your_username
FINTS_PIN=your_pin
FINTS_SERVER=https://banking.example.com/fints
FINTS_PRODUCT_ID=YOUR_PRODUCT_ID
```


## Limitations

- FinTS 3.0 only (older HBCI versions not supported)
- PIN/TAN authentication only (signature cards not supported)
- Read-only operations (transfers not supported)
- German banks only (banks supporting FinTS/HBCI)

## Development

### Running Tests

```bash
# Unit tests
poetry run pytest tests/unit/

# Integration tests (requires credentials in .env)
poetry run pytest tests/integration/ --run-integration
```

### Code Quality

```bash
poetry run ruff check geldstrom/
poetry run ruff format geldstrom/
```

## Credits

Geldstrom builds on the foundation laid by [python-fints](https://github.com/raphaelm/python-fints), an open-source FinTS implementation created and maintained by [Raphael Michel](https://github.com/raphaelm).

## License

Business Source License 1.1 (BUSL-1.1)

This software is source-available but not open source. You may use it for non-production purposes. Production use requires a commercial license.

On January 1, 2029, this software will be released under the Apache License 2.0.
