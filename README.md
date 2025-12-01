# Geldstrom

**German banking made simple.** Access your bank accounts, fetch transactions, and check balances programmatically.

Geldstrom is a pure-Python implementation of the FinTS/HBCI protocol, the standard interface for online banking with German banks.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: LGPL v3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)

## Features

- **Read-only access** to German bank accounts
- **Fetch transactions** with date range filtering
- **Check balances** across multiple accounts
- **List accounts** and their capabilities
- **Decoupled TAN support** (push notifications via banking apps like SecureGo)
- **Type-safe** with Pydantic models
- **No external dependencies** on banking software

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
from geldstrom.clients import ReadOnlyFinTSClient
from geldstrom.domain.model import BankRoute, FinTSCredentials

# Configure your bank connection
credentials = FinTSCredentials(
    bank_route=BankRoute(country_code="280", bank_code="12345678"),
    user_id="your_username",
    pin="your_pin",
    fints_url="https://your-bank.example/fints",
)

# Connect and fetch data
with ReadOnlyFinTSClient(credentials) as client:
    # List all accounts
    accounts = client.list_accounts()
    for account in accounts:
        print(f"Account: {account.iban}")

    # Get balance for first account
    if accounts:
        balance = client.get_balance(accounts[0].account_id)
        print(f"Balance: {balance.amount} {balance.currency}")

    # Fetch recent transactions
    transactions = client.get_transactions(accounts[0].account_id)
    for tx in transactions.entries:
        print(f"{tx.date}: {tx.amount} - {tx.purpose}")
```

## Supported Operations

| Operation | Description |
|-----------|-------------|
| `list_accounts()` | List all accessible bank accounts |
| `get_balance(account_id)` | Fetch current balance for an account |
| `get_transactions(account_id, start_date, end_date)` | Fetch transaction history |
| `list_statements(account_id)` | List available bank statements |
| `get_statement(account_id, statement_id)` | Download a specific statement |

## TAN Handling

Geldstrom supports decoupled TAN methods (like SecureGo or pushTAN). When a TAN is required:

1. You'll receive a push notification in your banking app
2. Approve the request in the app
3. Geldstrom automatically polls for confirmation and continues

```python
# TAN handling is automatic - just approve in your banking app
transactions = client.get_transactions(
    account_id,
    start_date=date.today() - timedelta(days=90),  # May require TAN
)
```

## Configuration

### Environment Variables

For convenience, you can configure credentials via environment variables:

```bash
export FINTS_BLZ=12345678
export FINTS_COUNTRY=DE
export FINTS_USER=your_username
export FINTS_PIN=your_pin
export FINTS_SERVER=https://your-bank.example/fints
```

### Finding Your Bank's FinTS URL

Most German banks publish their FinTS server URLs. Common patterns:

- Sparkassen: `https://banking-[region].s-fints-pt-[region].de/fints30`
- Volksbanken: `https://fints.gad.de/fints`
- Deutsche Bank: `https://fints.deutsche-bank.de/`

Check your bank's online banking documentation or contact their support.

## Limitations

- **FinTS 3.0 only** - Older HBCI versions are not supported
- **PIN/TAN only** - Signature cards (HBCI chipcard) are not supported
- **Read-focused** - Write operations (transfers) have limited support
- **German banks** - Only banks supporting FinTS/HBCI (primarily German)

## Development

### Running Tests

```bash
# Unit tests (no bank connection required)
poetry run pytest tests/unit

# Integration tests (requires real credentials in .env)
poetry run pytest tests/integration --run-integration
```

### Integration Test Setup

Create a `.env` file:

```env
FINTS_BLZ=12345678
FINTS_COUNTRY=DE
FINTS_USER=your_username
FINTS_PIN=your_pin
FINTS_SERVER=https://your-bank.example/fints
FINTS_PRODUCT_ID=YOUR_PRODUCT_ID
FINTS_PRODUCT_VERSION=1.0.0
```

> **Note:** Integration tests may trigger TAN prompts. Be ready to approve them in your banking app.

### Code Quality

```bash
# Linting
poetry run ruff check geldstrom/

# Formatting
poetry run ruff format geldstrom/
```

## Security

If you discover a security issue, please report it responsibly:

- **Email:** security@pretix.eu
- **Policy:** [Responsible Disclosure](https://docs.pretix.eu/trust/security/disclosure/)

**Important:** Never commit your banking credentials to version control!

## Credits

Originally developed as [python-fints](https://github.com/raphaelm/python-fints) by:

- **Raphael Michel** - Original author and maintainer
- **Henryk Plötz** - Major contributions

Additional contributors: Daniel Nowak, Patrick Braune, Mathias Dalheimer, Christopher Grebs, Markus Schindler, and many more.

## License

LGPL-3.0-or-later

This means you can use this library in proprietary software, but any modifications to the library itself must be released under the same license.
