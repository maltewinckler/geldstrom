# Geldstrom

Access German bank accounts programmatically. Geldstrom is a pure-Python FinTS 3.0 client and a self-hostable banking gateway for reading accounts, balances, and transaction history from Sparkassen, Volksbanken, Deutsche Bank, DKB, and most other German financial institutions.

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: LGPL v3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0.en.html)

## Monorepo layout

| Component | Path | Description |
|-----------|------|-------------|
| **geldstrom** | `packages/geldstrom/` | Pure-Python FinTS 3.0 client library |
| **gateway** | `apps/gateway/` | FastAPI banking gateway (REST for FinTS) |
| **gateway-admin** | `apps/gateway_admin/` | Admin web UI and CLI for managing the gateway |
| **geldstrom-cli** | `packages/geldstrom_cli/` | Minimal developer CLI for manual gateway testing |

## Quick start with library

```python
from geldstrom import FinTS3Client

with FinTS3Client(
    bank_code="12345678",
    server_url="https://banking.example.com/fints",
    user_id="your_username",
    pin="your_pin",
    product_id="YOUR_PRODUCT_ID",
    tan_method="946",
) as client:
    for account in client.list_accounts():
        balance = client.get_balance(account)
        print(f"{account.iban}: {balance.booked.amount} {balance.booked.currency}")
```

For banks that require app-based 2FA (SecureGo+, pushTAN, ...) without blocking, use `FinTS3ClientDecoupled` - see `packages/geldstrom/README.md` and `examples/`.

> **Product ID**: Registration with the [Deutsche Kreditwirtschaft](https://www.fints.org/de/hersteller/produktregistrierung) is required and free.

## Quick start with gateway (Docker)

```bash
cp config/admin_cli.env.example config/admin_cli.env   # fill in passwords + SMTP
cp config/gateway.env.example   config/gateway.env     # fill in passwords

docker compose up -d
```

The `gateway-admin` container initialises the database schema on first startup, then serves the admin UI at `http://localhost:8001` (SSH port-forward only - not exposed publicly).

**Load the institute catalog** (required before the gateway accepts banking requests):

```bash
docker compose exec gateway-admin gw-admin catalog sync /data/fints_institute.csv
```

**Create your first API consumer** (token is emailed automatically):

```bash
docker compose exec gateway-admin gw-admin users create you@example.com
```

**Verify the gateway is ready:**

```bash
curl http://localhost:8000/health/ready
# {"status":"ready","checks":{"db":"ok","product_key":"loaded","catalog":"ok"}}
```

Full setup guide: `docs/developer/getting-started.md`

## API reference (`geldstrom` library)

### `FinTS3Client`

```python
from geldstrom import FinTS3Client, TANConfig

FinTS3Client(
    bank_code: str,                      # BLZ, e.g. "12345678"
    server_url: str,                     # FinTS PIN/TAN URL
    user_id: str,                        # Online banking username
    pin: str,                            # Online banking PIN
    product_id: str,                     # FinTS product registration ID
    *,
    country_code: str = "DE",
    customer_id: str | None = None,      # Defaults to user_id
    tan_medium: str | None = None,       # TAN device name (e.g. "SecureGo+")
    tan_method: str | None = None,       # TAN method code (e.g. "946")
    product_version: str = "1.0",
    session_state: FinTSSessionState | None = None,
    challenge_handler: ChallengeHandler | None = None,
    tan_config: TANConfig | None = None,
)
```

#### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `connect()` | `Sequence[Account]` | Open dialog and discover accounts |
| `disconnect()` | `None` | Close session |
| `list_accounts()` | `Sequence[Account]` | Return cached accounts (calls `connect()` if needed) |
| `get_account(account_id)` | `Account` | Look up account by ID |
| `get_balance(account)` | `BalanceSnapshot` | Fetch current balance |
| `get_balances(account_ids)` | `Sequence[BalanceSnapshot]` | Fetch multiple balances in one dialog |
| `get_transactions(account, start_date, end_date)` | `TransactionFeed` | Fetch transaction history |
| `get_tan_methods()` | `Sequence[TANMethod]` | List TAN methods from BPD |

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `session_state` | `FinTSSessionState \| None` | Serializable session state |
| `capabilities` | `BankCapabilities \| None` | Bank-advertised supported operations |
| `is_connected` | `bool` | Whether a live dialog is open |
| `tan_config` | `TANConfig` | Current TAN polling config |

### Domain models

#### `Account`

| Field | Type | Description |
|-------|------|-------------|
| `account_id` | `str` | `"<account_number>:<subaccount>"` |
| `iban` | `str \| None` | IBAN |
| `bic` | `str \| None` | BIC/SWIFT |
| `currency` | `str \| None` | Currency code |
| `product_name` | `str \| None` | Product label from the bank |
| `owner` | `AccountOwner \| None` | Account holder name and address |
| `bank_route` | `BankRoute` | Country code + BLZ |
| `capabilities` | `AccountCapabilities` | Supported operations |

#### `BalanceSnapshot`

| Field | Type | Description |
|-------|------|-------------|
| `account_id` | `str` | Account identifier |
| `as_of` | `datetime` | Timestamp of the balance |
| `booked` | `BalanceAmount` | Confirmed balance |
| `pending` | `BalanceAmount \| None` | Pending (unconfirmed) |
| `available` | `BalanceAmount \| None` | Available balance |
| `credit_limit` | `BalanceAmount \| None` | Credit limit |

#### `TransactionEntry`

| Field | Type | Description |
|-------|------|-------------|
| `entry_id` | `str` | Stable entry identifier |
| `booking_date` | `date` | Booking date |
| `value_date` | `date` | Value date |
| `amount` | `Decimal` | Positive = credit, negative = debit |
| `currency` | `str` | Transaction currency |
| `purpose` | `str` | Remittance text |
| `counterpart_name` | `str \| None` | Other party name |
| `counterpart_iban` | `str \| None` | Other party IBAN |

## Gateway API

The gateway exposes a JSON REST API at `http://localhost:8000`.

### Authentication

All banking endpoints require `Authorization: Bearer <api-key>`.

### Banking endpoints

#### `POST /v1/banking/accounts`

```json
{
  "protocol": "fints",
  "blz": "12345678",
  "user_id": "your-bank-login",
  "password": "your-bank-pin",
  "tan_method": "946"
}
```

Returns `200` with account list, or `202` with `operation_id` if TAN confirmation is required.

#### `POST /v1/banking/transactions`

```json
{
  "protocol": "fints",
  "blz": "12345678",
  "user_id": "your-bank-login",
  "password": "your-bank-pin",
  "iban": "DE89370400440532013000",
  "start_date": "2026-01-01",
  "end_date": "2026-04-07",
  "tan_method": "946"
}
```

#### `POST /v1/banking/operations/{operation_id}/poll`

Resume a pending TAN operation. Terminal states: `completed`, `failed`, `expired`.

### Health endpoints


```bash
GET /health/live    # → {"status":"ok"}
GET /health/ready   # → {"status":"ready","checks":{"db":"ok","product_key":"loaded","catalog":"ok"}}
```

## Development

```bash
uv sync

uv run pytest tests/apps tests/unit tests/packages/geldstrom/unit -x -q

uv run ruff check .
uv run ruff format .
```

See `docs/developer/getting-started.md` for the full local setup guide.

## License

LGPL-3.0-only - see [LICENSE](LICENSE).
