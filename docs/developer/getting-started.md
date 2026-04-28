# Getting Started

This guide covers running a local gateway instance - either via **Docker Compose** (recommended) or **directly on the host** (for development).

## Option A - Docker Compose

### 1. Configure secrets

```bash
cp config/admin_cli.env.example config/admin_cli.env
cp config/gateway.env.example   config/gateway.env
```

Edit both files. At minimum:

- `config/admin_cli.env`: set `POSTGRES_PASSWORD`, `GATEWAY_DB_PASSWORD`, `FINTS_PRODUCT_REGISTRATION_KEY`, and your SMTP credentials
- `config/gateway.env`: set `GATEWAY_DB_PASSWORD` (must match the value above)

### 2. Start the stack

```bash
docker compose up -d
```

This starts PostgreSQL, Redis, the gateway, and the admin service. The `gateway-admin` container initialises the database schema automatically on first startup - no separate init step needed.

Wait until the gateway is healthy:

```bash
docker compose ps
# gateway-admin should be "running", gateway should be "healthy"
```

### 3. Load the institute catalog

The gateway needs the Bundesbank FinTS institute catalog before it can route banking requests. The CSV is included in the repo at `data/fints_institute.csv`.

```bash
docker compose exec gateway-admin gw-admin catalog sync /data/fints_institute.csv
```

This takes a few seconds and is idempotent - safe to run again after updates.

### 4. Create your first API consumer

```bash
docker compose exec gateway-admin gw-admin users create you@example.com
```

The API token is emailed to the address you provide. Make sure SMTP is configured in `config/admin_cli.env` before running this.

### 5. Verify readiness

```bash
curl http://localhost:8000/health/ready
```

Expected response:

```json
{"status":"ready","checks":{"db":"ok","product_key":"loaded","catalog":"ok"}}
```

If any check fails, run `docker compose exec gateway-admin gw-admin inspect state` to see what's missing.

## Option B - Running directly on the host

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

Copy the examples and fill in values:

**`config/admin_cli.env`**

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

SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=you@example.com
SMTP_PASSWORD=your_smtp_password
SMTP_FROM_EMAIL=noreply@example.com
SMTP_USE_TLS=true
```

**`config/gateway.env`**

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

Creates the database, all tables, the restricted `gateway` DB user, and stores the product key from the env file. Idempotent.

### 4. Start the gateway

```bash
uvicorn gateway.presentation.http.api:create_app --factory --host 0.0.0.0 --port 8000
```

### 5. Complete setup

```bash
uv run gw-admin catalog sync data/fints_institute.csv
uv run gw-admin users create you@example.com
curl http://localhost:8000/health/ready
```

## Admin UI

The admin web UI runs on port 8001 inside Docker. It is bound to `127.0.0.1` and not exposed publicly - access it via SSH port-forwarding:

```bash
ssh -L 8001:localhost:8001 user@your-vps
```

Then open `http://localhost:8001` in your browser.

From the UI you can list users, create new ones (token delivered by email), reroll tokens, disable, and delete users.

## Admin CLI reference

The `gw-admin` CLI is available inside the container or locally via `uv run gw-admin`.

```bash
gw-admin db init                                          # Create DB, schema, gateway user
gw-admin catalog sync <path-to-csv>                       # Load/refresh institute catalog
gw-admin product update <key> --product-version <ver>     # Store FinTS product key manually
gw-admin users list
gw-admin users create <email>                             # Token sent by email
gw-admin users update <id> --email <new>
gw-admin users disable <id>
gw-admin users reactivate <id>
gw-admin users rotate-key <id>                            # Issue new token, sent by email
gw-admin users delete <id> --confirm
gw-admin inspect state [--blz <blz>]                      # Show backend state
```

## Gateway configuration reference

All gateway settings are prefixed `GATEWAY_` and read from `config/gateway.env`.

| Variable | Default | Description |
|----------|---------|-------------|
| `GATEWAY_DB_USER` | `gateway` | PostgreSQL username |
| `GATEWAY_DB_PASSWORD` | - | **Required** |
| `GATEWAY_DB_HOST` | `localhost` | PostgreSQL host (`postgres` inside Docker) |
| `GATEWAY_DB_PORT` | `5432` | PostgreSQL port |
| `GATEWAY_DB_NAME` | `geldstrom` | Database name |
| `GATEWAY_FINTS_PRODUCT_VERSION` | `1.0.0` | FinTS product version string |
| `GATEWAY_OPERATION_SESSION_TTL_SECONDS` | `120` | Pending TAN session lifetime |
| `GATEWAY_RATE_LIMIT_REQUESTS_PER_MINUTE` | `60` | Per-process rate limit |
| `GATEWAY_HOST` | `0.0.0.0` | Bind address |
| `GATEWAY_PORT` | `8000` | Bind port |
| `GATEWAY_LOG_LEVEL` | `INFO` | Log level |
| `GATEWAY_JSON_LOGS` | `true` | Emit structured JSON logs |

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

### Decoupled TAN (2FA)

If the bank requires app-based confirmation, the response is `202 Accepted` with an `operation_id`. Approve the TAN in your banking app, then poll:

```bash
curl -s -X POST http://localhost:8000/v1/banking/operations/<operation-id>/poll \
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

Poll until `status` is `completed` or `failed`. Completed operations include the full result in `result_payload`.

### Health checks

```bash
curl http://localhost:8000/health/live    # {"status":"ok"}
curl http://localhost:8000/health/ready  # {"status":"ready","checks":{...}}
```

## Developer tools

```bash
# Interactive CLI wrapping the gateway API
uv run geldstrom-cli accounts

# Run tests
uv run pytest tests/apps tests/unit tests/packages/geldstrom/unit -x -q

# Lint
uv run ruff check .
```

Interactive API docs: `http://localhost:8000/docs`
