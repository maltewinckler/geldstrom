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
| `list_statements(account)` | List available statements | `Sequence[StatementReference]` |
| `get_statement(reference)` | Download a statement | `StatementDocument` |

#### Properties

| Property | Description | Type |
|----------|-------------|------|
| `is_connected` | Connection status | `bool` |
| `capabilities` | Bank's advertised capabilities | `BankCapabilities` |
| `session_state` | Current session for persistence | `SessionToken` |

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
| `booked` | `BalanceAmount` | Booked balance |
| `available` | `BalanceAmount` | Available balance (if provided) |
| `as_of` | `datetime` | Timestamp of the balance |

#### TransactionFeed

Collection of transactions.

| Field | Type | Description |
|-------|------|-------------|
| `account_id` | `str` | Account identifier |
| `start_date` | `date` | Start of date range |
| `end_date` | `date` | End of date range |
| `entries` | `list[TransactionEntry]` | Transaction entries |

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

The default timeout for TAN approval is 120 seconds.

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

### Finding Your Bank's FinTS URL

Common patterns:

- **Sparkassen:** `https://banking-[region].s-fints-pt-[region].de/fints30`
- **Volksbanken:** `https://fints.gad.de/fints`
- **Deutsche Bank:** `https://fints.deutsche-bank.de/`
- **DKB:** `https://banking-dkb.s-fints-pt-dkb.de/fints30`

Check your bank's online banking documentation or contact support.

### Product Registration

To use FinTS, you need a registered product ID. Register at [hbci-zka.de](https://www.hbci-zka.de/register/prod_register.htm).

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

## Security

Report security issues to: security@pretix.eu

Never commit banking credentials to version control.

## Credits

Geldstrom builds on the foundation laid by [python-fints](https://github.com/raphaelm/python-fints), an open-source FinTS implementation created and maintained by [Raphael Michel](https://github.com/raphaelm).

## License

Business Source License 1.1 (BUSL-1.1)

This software is source-available but not open source. You may use it for non-production purposes. Production use requires a commercial license.

On January 1, 2029, this software will be released under the Apache License 2.0.
