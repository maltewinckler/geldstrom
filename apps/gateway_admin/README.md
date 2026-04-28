# gateway-admin

Administrative tooling for the Geldstrom gateway. Ships two entry points:

- **`gw-admin`** — CLI for one-shot operations (DB init, catalog sync, user management)
- **`gw-admin-api`** — FastAPI service that backs the React admin UI

Both share the same application layer, domain model, and database.

## Architecture

```
gateway_admin/
├── domain/               # Entities, value objects, repository protocols, domain services
│   ├── audit/            # AuditEvent, AuditEventType, AuditQueryRepository
│   ├── entities/         # User, FinTSInstitute, ProductRegistration
│   ├── repositories/     # UserRepository (with UserQuery/UserPage), InstituteRepository, ProductRepository
│   ├── services/         # AdminApiKeyService, EmailService, GatewayNotificationService, IdProvider, InstituteCsvReaderPort
│   └── value_objects/    # Email, UserId, ApiKeyHash, BankLeitzahl, Bic, …
├── application/
│   ├── commands/         # CreateUser, DeleteUser, DisableUser, ReactivateUser, RotateUserKey,
│   │                     #   SyncInstituteCatalog, UpdateProductRegistration, InitializeAdmin
│   ├── queries/          # ListUsers (paginated + filtered), GetUser, ListAuditEvents, InspectBackendState
│   ├── dtos/             # UserSummary, UserKeyResult, BackendStateReport, InstituteCatalogSyncResult, …
│   └── factories/        # AdminRepositoryFactory, ServiceFactory (protocols)
├── infrastructure/
│   ├── persistence/sqlalchemy/
│   │   ├── repositories/ # UserRepositorySQLAlchemy, AuditRepositorySqlAlchemy,
│   │   │                 #   InstituteRepositorySQLAlchemy, ProductRepositorySQLAlchemy
│   │   └── factories/    # AdminRepositoryFactorySQLAlchemy, ServiceFactorySQLAlchemy
│   └── services/         # Argon2ApiKeyService, AiosmtplibEmailService, IdProvider, InstituteCsvReader
└── presentation/
    ├── api/              # FastAPI app (main.py, routes.py, schemas.py, dependencies.py)
    └── cli/              # Typer app (db, users, catalog, product, inspect sub-commands)

frontend/                 # React + Vite admin UI (served as static files by the API)
```

## REST API

The API runs on port `8001` by default and serves the React UI at `/`. All data endpoints are under `/`.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/users` | List users — supports `?email=`, `?status=`, `?page=`, `?page_size=` |
| `GET` | `/users/{user_id}` | Get a single user by ID |
| `POST` | `/users` | Create a user; raw API key returned once |
| `POST` | `/users/{user_id}/reroll` | Rotate API key; new raw key returned once |
| `POST` | `/users/{user_id}/disable` | Disable a user |
| `POST` | `/users/{user_id}/reactivate` | Reactivate a disabled user |
| `DELETE` | `/users/{user_id}` | Permanently delete a user |
| `POST` | `/catalog/sync` | Upload a Bundesbank CSV to replace the institute catalog |
| `GET` | `/audit` | Query audit events — supports `?consumer_id=`, `?event_type=`, `?from_date=`, `?to_date=`, `?page=`, `?page_size=` |

Interactive docs are available at `/docs` when the server is running.

The API has no authentication — access is restricted to SSH port-forwarding (`127.0.0.1:8001`).

## CLI reference

### `gw-admin db`

| Command | Description |
|---------|-------------|
| `db init` | Create tables and the restricted gateway DB user (idempotent). Also seeds the FinTS product registration from env. |
| `db reset` | Delete all rows from every table (structure kept). Requires `--yes`. |

### `gw-admin users`

| Command | Description |
|---------|-------------|
| `users list` | List all API consumers |
| `users create <email>` | Create a new consumer; prints the raw API key **once** |
| `users update <id> --email <new>` | Update a consumer's email |
| `users disable <id>` | Disable a consumer (key stops working immediately) |
| `users reactivate <id>` | Re-enable a disabled consumer and issue a fresh key |
| `users rotate-key <id>` | Issue a new API key; old key is invalidated immediately |
| `users delete <id> --confirm` | Permanently delete a consumer |

### `gw-admin catalog`

| Command | Description |
|---------|-------------|
| `catalog sync <csv-path>` | Replace the institute catalog from a Bundesbank CSV (fires `gw.catalog_replaced` NOTIFY) |

### `gw-admin product`

| Command | Description |
|---------|-------------|
| `product update <key> --product-version <ver>` | Store or replace the FinTS product registration key |

### `gw-admin inspect`

| Command | Description |
|---------|-------------|
| `inspect state [--blz <blz>]` | Print DB connectivity, user count, institute count, and product registration status |

## Configuration

All configuration is via environment variables (or a `.env` file). Key settings:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Async PostgreSQL URL (`postgresql+asyncpg://…`) |
| `FINTS_PRODUCT_REGISTRATION_KEY` | FinTS product key — seeded automatically by `db init` and on API startup |
| `FINTS_PRODUCT_VERSION` | FinTS product version string |
| `SMTP_HOST` / `SMTP_PORT` | SMTP server for sending API key emails |
| `SMTP_FROM` | Sender address for key emails |
| `ADMIN_UI_PORT` | Port the API listens on (default: `8001`) |

## Running locally

```sh
# CLI
uv run gw-admin --help

# API server (requires a built frontend or FRONTEND_DIR pointing elsewhere)
uv run uvicorn gateway_admin.presentation.api.main:app --port 8001

# Frontend dev server (proxies API calls to :8001)
cd frontend && npm install && npm run dev
```

## Docker

```sh
# One-shot CLI commands
docker compose run --rm gateway-admin gw-admin db init
docker compose run --rm gateway-admin gw-admin catalog sync /data/fints_institute.csv
docker compose run --rm gateway-admin gw-admin users create you@example.com

# The API + UI runs as a long-lived service
docker compose up gateway-admin
```
