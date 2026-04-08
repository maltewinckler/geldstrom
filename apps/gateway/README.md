# gateway

FastAPI HTTP service that turns bank credentials into structured JSON. It wraps the `geldstrom` FinTS client, handles decoupled (app-based) 2FA flows asynchronously, and manages consumers and the FinTS institute catalog in PostgreSQL.

## What it does

- Accepts bank credentials (`blz`, `user_id`, `password`) and returns accounts, balances, or transactions
- Responds synchronously (`200`) when the bank answers immediately, or asynchronously (`202` + polling URL) when a TAN confirmation is required
- Authenticates API consumers via Argon2id-hashed Bearer tokens
- Keeps the FinTS institute catalog and API consumer records in PostgreSQL; caches them in memory
- Reacts to `gw.catalog_replaced` and `gw.consumer_updated` PostgreSQL NOTIFY events (via `PostgresNotifyListener`) to refresh in-memory caches without a restart
- Runs a background resume worker that polls pending decoupled-TAN sessions every 5 seconds
- Rates-limit incoming requests per-process (in-memory, single-worker safe)

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health/live` | Liveness ping — always 200 if the process is up |
| GET | `/health/ready` | Readiness — checks DB, product key, and institute catalog |
| POST | `/v1/banking/accounts` | List bank accounts |
| POST | `/v1/banking/balances` | Get account balances |
| POST | `/v1/banking/transactions` | Fetch transaction history |
| POST | `/v1/banking/tan-methods` | List available TAN methods |
| GET | `/v1/banking/operations/{id}` | Poll a pending 2FA operation |

All `/v1/banking/*` routes require `Authorization: Bearer <api-key>`.

Interactive API docs are served at `/docs` (Swagger UI) and `/redoc`.

## Architecture

```
Presentation (FastAPI routers / HTTP schemas)
        │
Application (commands + queries: ListAccounts, FetchTransactions, …)
        │
Domain (BankingConnector protocol, OperationStatus, PendingOperationSession)
        │
Infrastructure
  ├── banking/geldstrom/   GeldstromBankingConnector → FinTS3ClientDecoupled
  ├── banking/protocols/   BankingConnectorDispatcher (route by protocol)
  ├── persistence/sql/     SQLAlchemy async repositories (consumers, institutes, product)
  ├── cache/memory/        In-memory consumer/institute caches + operation session store
  ├── crypto/              Argon2ApiKeyService
  └── readiness/           SQLGatewayReadinessService
```

The application factory (`GatewayApplicationFactory`) wires everything together at startup.

## Configuration

Copy `config/gateway.env.example` to `config/gateway.env` and fill in the values. All settings are prefixed `GATEWAY_`.

| Variable | Default | Description |
|----------|---------|-------------|
| `GATEWAY_DB_USER` | `gateway` | PostgreSQL username |
| `GATEWAY_DB_PASSWORD` | — | **Required.** PostgreSQL password |
| `GATEWAY_DB_HOST` | `localhost` | PostgreSQL host (`postgres` inside Docker) |
| `GATEWAY_DB_PORT` | `5432` | PostgreSQL port |
| `GATEWAY_DB_NAME` | `geldstrom` | Database name |
| `GATEWAY_ARGON2_TIME_COST` | `2` | Argon2id time cost |
| `GATEWAY_ARGON2_MEMORY_COST` | `65536` | Argon2id memory cost (kB) |
| `GATEWAY_ARGON2_PARALLELISM` | `2` | Argon2id parallelism |
| `GATEWAY_OPERATION_SESSION_TTL_SECONDS` | `120` | Pending TAN session lifetime |
| `GATEWAY_OPERATION_SESSION_MAX_COUNT` | `10000` | Max concurrent pending sessions |
| `GATEWAY_RATE_LIMIT_REQUESTS_PER_MINUTE` | `60` | Per-process rate limit |
| `GATEWAY_NOTIFY_RECONNECT_BACKOFF_SECONDS` | `1.0` | Backoff on LISTEN reconnect |
| `GATEWAY_FINTS_PRODUCT_VERSION` | `1.0.0` | FinTS product version string |
| `GATEWAY_HOST` | `0.0.0.0` | Bind address |
| `GATEWAY_PORT` | `8000` | Bind port |
| `GATEWAY_WORKERS` | `1` | uvicorn worker count (keep at 1 — rate-limiter is in-process) |
| `GATEWAY_LOG_LEVEL` | `INFO` | Log level |
| `GATEWAY_JSON_LOGS` | `true` | Emit structured JSON logs |

## Running locally

```bash
# From the workspace root (with uv):
uv run gateway-server
# Or via uvicorn directly:
uvicorn gateway.presentation.http.api:create_app --factory --host 0.0.0.0 --port 8000
```

The server requires an initialized database. Use `gw-admin db init` (see the admin CLI README) to create the schema and DB user before starting the gateway.

## First-run setup

After starting the stack for the first time, three steps are needed before banking requests will succeed:

1. **Load the institute catalog**: `gw-admin catalog sync /data/fints_institute.csv`
2. **Store the FinTS product key**: `gw-admin product update "<KEY>" --product-version "1.0.0"`
3. **Create an API consumer**: `gw-admin users create you@example.com` (key shown once)

See `docs/developer/getting-started.md` for the complete walkthrough.
