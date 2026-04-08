# Geldstrom

Access German bank accounts programmatically. Geldstrom is a pure-Python FinTS 3.0 client and a self-hostable banking gateway for reading accounts, balances, and transaction history from Sparkassen, Volksbanken, Deutsche Bank, DKB, and most other German financial institutions.

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: LGPL v3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0.en.html)

---

## Monorepo layout

| Component | Path | Description |
|-----------|------|-------------|
| **geldstrom** | `packages/geldstrom/` | Pure-Python FinTS 3.0 client library |
| **gateway** | `apps/gateway/` | FastAPI banking gateway (REST → FinTS) |
| **gateway-admin-cli** | `apps/gateway_admin_cli/` | Admin CLI for managing the gateway DB |
| **gateway-contracts** | `packages/gateway-contracts/` | Shared SQLAlchemy schema and NOTIFY channels |
| **geldstrom-cli** | `packages/geldstrom_cli/` | Developer CLI for manual gateway testing |

Data: `data/fints_institute.csv` — Bundesbank-sourced FinTS institute catalog (BLZ → PIN-TAN URL).

---

## Quick start — library

```python
from geldstrom import FinTS3Client

with FinTS3Client(
    bank_code="12345678",
    server_url="https://banking.example.com/fints",
    user_id="your_username",
    pin="your_pin",
    product_id="YOUR_PRODUCT_ID",   # register at fints.org (free)
    tan_method="946",               # required by most banks
) as client:
    for account in client.list_accounts():
        balance = client.get_balance(account)
        print(f"{account.iban}: {balance.booked.amount} {balance.booked.currency}")
```

For banks that require app-based 2FA (SecureGo+, pushTAN, …) without blocking, use `FinTS3ClientDecoupled` — see `packages/geldstrom/README.md` and `examples/`.

> **Product ID**: Registration with the [Deutsche Kreditwirtschaft](https://www.fints.org/de/hersteller/produktregistrierung) is required and free; responses typically come within days.

---

## Quick start — gateway (Docker)

```bash
cp config/admin_cli.env.example config/admin_cli.env   # fill in passwords
cp config/gateway.env.example   config/gateway.env     # fill in passwords

docker compose up -d

# One-time setup (run once after first start)
docker compose run --rm gateway-admin-cli gw-admin db init
docker compose run --rm gateway-admin-cli gw-admin catalog sync /data/fints_institute.csv
docker compose run --rm gateway-admin-cli gw-admin users create you@example.com
# → prints API key once; copy it

curl http://localhost:8000/health/ready
# → {"status":"ready","checks":{"db":"ok","product_key":"loaded","catalog":"ok"}}
```

Full walkthrough: `docs/developer/getting-started.md`

---

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
    session_state: FinTSSessionState | None = None,  # Resume existing session
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
| `get_transactions(account, start_date, end_date)` | `TransactionFeed` | Fetch transaction history (MT940 preferred, CAMT fallback) |
| `get_tan_methods()` | `Sequence[TANMethod]` | List TAN methods from BPD (no TAN required) |

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `session_state` | `FinTSSessionState \| None` | Serializable session; persist to skip re-sync next time |
| `capabilities` | `BankCapabilities \| None` | Bank-advertised supported operations |
| `is_connected` | `bool` | Whether a live dialog is open |
| `tan_config` | `TANConfig` | Current TAN polling config (settable) |

#### Context manager

```python
with FinTS3Client(...) as client:
    # connect() called automatically on __enter__
    accounts = client.list_accounts()
# disconnect() called automatically on __exit__
```

### Domain models

#### `Account`

| Field | Type | Description |
|-------|------|-------------|
| `account_id` | `str` | `"<account_number>:<subaccount>"` |
| `iban` | `str \| None` | IBAN |
| `bic` | `str \| None` | BIC/SWIFT |
| `currency` | `str \| None` | Currency code (e.g. `"EUR"`) |
| `product_name` | `str \| None` | Product label from the bank |
| `owner` | `AccountOwner \| None` | Account holder name and address |
| `bank_route` | `BankRoute` | Country code + BLZ |
| `capabilities` | `AccountCapabilities` | What operations the bank allows |

#### `BalanceSnapshot`

| Field | Type | Description |
|-------|------|-------------|
| `account_id` | `str` | Account identifier |
| `as_of` | `datetime` | Timestamp of the balance |
| `booked` | `BalanceAmount` | Confirmed balance |
| `pending` | `BalanceAmount \| None` | Pending (unconfirmed) |
| `available` | `BalanceAmount \| None` | Available balance (may differ from booked due to holds) |
| `credit_limit` | `BalanceAmount \| None` | Credit limit |

#### `TransactionFeed`

| Field | Type | Description |
|-------|------|-------------|
| `account_id` | `str` | Account identifier |
| `entries` | `Sequence[TransactionEntry]` | Transactions in date range |
| `start_date` | `date` | Requested range start |
| `end_date` | `date` | Requested range end |
| `has_more` | `bool` | Whether pagination cut off results |

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

---

## Gateway API

The gateway exposes a JSON REST API at `http://localhost:8000` (Docker) or configured host/port.

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

#### `POST /v1/banking/balances`

Same input shape as `/accounts`.

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

#### `POST /v1/banking/tan-methods`

Same input shape as `/accounts` (no IBAN needed). Returns TAN methods advertised by the bank without requiring TAN confirmation.

#### `GET /v1/banking/operations/{operation_id}`

Poll a pending TAN operation. Terminal states: `completed`, `failed`, `expired`.

### Health endpoints

```bash
GET /health/live    # → {"status":"ok"}
GET /health/ready   # → {"status":"ready","checks":{"db":"ok","product_key":"loaded","catalog":"ok"}}
```

---

## Development

```bash
# Install all workspace packages in dev mode
uv sync

# Run tests (unit + app + package)
uv run pytest tests/apps tests/unit tests/packages/geldstrom/unit -x -q

# Lint and format
uv run ruff check .
uv run ruff format .
```

See `docs/developer/getting-started.md` for the full local setup guide.

---

## License

LGPL-3.0-only — see [LICENSE](LICENSE).
