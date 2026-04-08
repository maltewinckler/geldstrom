# Getting Started

This guide walks through running a local gateway instance from scratch — either via **Docker Compose** (simplest) or **directly on the host** (for development).

---

## Option A — Docker Compose (recommended)

### 1. Configure secrets

```bash
cp config/admin_cli.env.example config/admin_cli.env
cp config/gateway.env.example   config/gateway.env
```

Edit both files. At minimum set strong passwords for `POSTGRES_PASSWORD`, `GATEWAY_DB_PASSWORD`, and provide your `FINTS_PRODUCT_REGISTRATION_KEY`.

### 2. Start the stack

```bash
docker compose up -d
```

This starts PostgreSQL and the gateway. The `gateway-admin-cli` service runs once as part of startup (`gw-admin db init`) to create the schema and the restricted gateway DB user.

### 3. Post-install checklist

> **These steps are required before the gateway will accept banking requests.**

**Load the institute catalog:**

```bash
docker compose run --rm gateway-admin-cli \
  gw-admin catalog sync /data/fints_institute.csv
```

**Create your first API consumer:**

```bash
docker compose run --rm gateway-admin-cli \
  gw-admin users create you@example.com
```

The raw API key is printed exactly once — copy it immediately.

**Verify readiness:**

```bash
curl http://localhost:8000/health/ready
# Expected: {"status":"ready","checks":{"db":"ok","product_key":"loaded","catalog":"ok"}}
```

If a check fails, see the diagnostic command below:

```bash
docker compose run --rm gateway-admin-cli gw-admin inspect state
```

---

## Option B — Running directly on the host

### 1. Start PostgreSQL

```bash
docker run -d \
  --name geldstrom-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=geldstrom \
  -p 5432:5432 \
  postgres:18-alpine
```

### 2. Configure environment

Both `config/admin_cli.env` and `config/gateway.env` are read relative to the workspace root. Copy the examples and fill in:

**`config/admin_cli.env`** (admin CLI)

```dotenv
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=geldstrom
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

FINTS_PRODUCT_REGISTRATION_KEY=your_key_here
FINTS_PRODUCT_VERSION=1.0.0

GATEWAY_DB_USER=gateway
GATEWAY_DB_PASSWORD=gateway_password
```

**`config/gateway.env`** (gateway service)

```dotenv
GATEWAY_DB_USER=gateway
GATEWAY_DB_PASSWORD=gateway_password
GATEWAY_DB_HOST=localhost
GATEWAY_DB_PORT=5432
GATEWAY_DB_NAME=geldstrom
GATEWAY_FINTS_PRODUCT_VERSION=1.0.0
```

### 3. Initialize the database

```bash
uv run gw-admin db init
```

This creates the database (if missing), all tables, the restricted `gateway` DB user, grants, and stores the product key from the env file. It is idempotent — safe to run again.

### 4. Start the gateway

```bash
uv run gateway-server
# or via uvicorn directly:
uvicorn gateway.presentation.http.api:create_app --factory --host 0.0.0.0 --port 8000
```

### 5. Complete setup

Same three steps as Option A:

```bash
uv run gw-admin catalog sync data/fints_institute.csv
uv run gw-admin users create you@example.com
curl http://localhost:8000/health/ready
```

---

## Gateway configuration reference

All gateway settings are prefixed `GATEWAY_` and read from `config/gateway.env`.

| Variable | Default | Description |
|----------|---------|-------------|
| `GATEWAY_DB_USER` | `gateway` | PostgreSQL username |
| `GATEWAY_DB_PASSWORD` | — | **Required** |
| `GATEWAY_DB_HOST` | `localhost` | PostgreSQL host (`postgres` inside Docker) |
| `GATEWAY_DB_PORT` | `5432` | PostgreSQL port |
| `GATEWAY_DB_NAME` | `geldstrom` | Database name |
| `GATEWAY_FINTS_PRODUCT_VERSION` | `1.0.0` | FinTS product version string |
| `GATEWAY_OPERATION_SESSION_TTL_SECONDS` | `120` | Pending TAN session lifetime |
| `GATEWAY_OPERATION_SESSION_MAX_COUNT` | `10000` | Max concurrent pending sessions |
| `GATEWAY_RATE_LIMIT_REQUESTS_PER_MINUTE` | `60` | Per-process rate limit |
| `GATEWAY_NOTIFY_RECONNECT_BACKOFF_SECONDS` | `1.0` | Backoff on LISTEN reconnect |
| `GATEWAY_HOST` | `0.0.0.0` | Bind address |
| `GATEWAY_PORT` | `8000` | Bind port |
| `GATEWAY_WORKERS` | `1` | Worker count (keep at 1 — in-process rate limiter) |
| `GATEWAY_LOG_LEVEL` | `INFO` | Log level |
| `GATEWAY_JSON_LOGS` | `true` | Emit structured JSON logs |

---

## Admin CLI reference

```bash
gw-admin db init                               # Create DB, schema, gateway user
gw-admin catalog sync <path-to-csv>            # Load/refresh institute catalog
gw-admin product update <key> --product-version <ver>  # Store FinTS product key
gw-admin users list
gw-admin users create <email>                  # Prints raw key once
gw-admin users update <id> --email <new>
gw-admin users disable <id>
gw-admin users reactivate <id>
gw-admin users rotate <id>                     # Issue new key
gw-admin users delete <id> --confirm
gw-admin inspect state [--blz <blz>]           # Show backend state
```

---

## Using the API

All `/v1/banking/*` endpoints require `Authorization: Bearer <api-key>`.

### List accounts

```bash
curl -s -X POST http://localhost:8000/v1/banking/accounts \
  -H "Authorization: Bearer <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "protocol": "fints",
    "blz": "12345678",
    "user_id": "your-bank-login",
    "password": "your-bank-pin",
    "tan_method": "946"
  }' | jq
```

### Fetch transactions

```bash
curl -s -X POST http://localhost:8000/v1/banking/transactions \
  -H "Authorization: Bearer <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "protocol": "fints",
    "blz": "12345678",
    "user_id": "your-bank-login",
    "password": "your-bank-pin",
    "iban": "DE89370400440532013000",
    "start_date": "2026-01-01",
    "end_date": "2026-04-07",
    "tan_method": "946"
  }' | jq
```

### Get available TAN methods

```bash
curl -s -X POST http://localhost:8000/v1/banking/tan-methods \
  -H "Authorization: Bearer <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "protocol": "fints",
    "blz": "12345678",
    "user_id": "your-bank-login",
    "password": "your-bank-pin"
  }' | jq
```

### Handling decoupled TAN (2FA)

If the bank requires app-based confirmation, the response is `202 Accepted` with an `operation_id`. Poll until `status` is `completed` or `failed`:

```bash
curl -s http://localhost:8000/v1/banking/operations/<operation-id> \
  -H "Authorization: Bearer <your-api-key>" | jq
```

Completed operations include the full result in `result_payload`. Pending operations expire after `GATEWAY_OPERATION_SESSION_TTL_SECONDS` (default 120 s).

### Health checks

```bash
curl http://localhost:8000/health/live    # {"status":"ok"}
curl http://localhost:8000/health/ready  # {"status":"ready","checks":{...}}
```

If `health/ready` returns `not_ready`, check which component failed and run the corresponding setup step.

---

## Developer tools

```bash
# Interactive CLI that wraps the gateway API
uv run geldstrom-cli accounts

# Run tests
uv run pytest tests/apps tests/unit tests/packages/geldstrom/unit -x -q

# Lint
uv run ruff check .
```

Interactive API docs are available at `http://localhost:8000/docs` while the gateway is running.
