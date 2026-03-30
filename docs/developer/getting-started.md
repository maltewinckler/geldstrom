# Getting Started

AI GENERATED!

This guide covers everything needed to run a local instance of the gateway API from scratch.

---

## 1. Initialize the database

Start a PostgreSQL container and create the `swen-gateway` database:

```bash
docker run -d \
  --name swen-gateway-postgres \
  -e POSTGRES_USER=gateway \
  -e POSTGRES_PASSWORD=gateway \
  -e POSTGRES_DB=swen-gateway \
  -p 5432:5432 \
  postgres:18-alpine
```

Then create the schema. The gateway-contracts package provides the SQLAlchemy metadata; use a one-shot Python script:

```bash
python - <<'EOF'
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from gateway_contracts.schema import metadata

async def main():
    engine = create_async_engine(
        "postgresql+asyncpg://gateway:gateway@localhost:5432/swen-gateway"
    )
    async with engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    await engine.dispose()
    print("Schema created.")

asyncio.run(main())
EOF
```

This creates three tables: `api_consumers`, `fints_institutes`, `fints_product_registration`.

---

## 2. Start the API

Set the required environment variable and launch with uvicorn:

```bash
export GATEWAY_DATABASE_URL="postgresql+asyncpg://gateway:gateway@localhost:5432/swen-gateway"

uvicorn gateway.presentation.http.api:create_app --factory --host 0.0.0.0 --port 8000
```

Optional settings (all have defaults):

| Variable | Default | Description |
|---|---|---|
| `GATEWAY_DATABASE_URL` | — | **Required.** asyncpg connection URL |
| `GATEWAY_ARGON2_TIME_COST` | `2` | Argon2id time cost for key hashing |
| `GATEWAY_ARGON2_MEMORY_COST` | `65536` | Argon2id memory cost (kB) |
| `GATEWAY_OPERATION_SESSION_TTL_SECONDS` | `120` | Timeout for pending TAN operations |
| `GATEWAY_FINTS_PRODUCT_VERSION` | `1.0.0` | FinTS product version string |

The API will be available at `http://localhost:8000`. Interactive docs are at `http://localhost:8000/docs`.

---

## 3. Create an API user and get an API key

The `gw-admin` CLI manages all administrative operations. It reads the database URL from `DATABASE_URL` (no prefix):

```bash
export DATABASE_URL="postgresql+asyncpg://gateway:gateway@localhost:5432/swen-gateway"

gw-admin users create alice@example.com
```

Output:

```
Created: alice@example.com (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)
Raw API key (shown once): <key>
```

**The raw key is shown exactly once — store it securely.** To rotate a key later:

```bash
gw-admin users rotate <user-id>
```

Other user commands:

```bash
gw-admin users list
gw-admin users update <user-id> --email new@example.com
gw-admin users disable <user-id>
gw-admin users delete <user-id> --confirm
```

---

## 4. Load institute catalog and product key

### FinTS institute catalog

Import the Bundesbank CSV export (semicolon-separated, latin-1 encoded):

```bash
gw-admin catalog sync /path/to/fints_institute.csv
```

Output: `Synced 1842 institutes.`

This is idempotent — running it again replaces the catalog atomically and fires a PostgreSQL `NOTIFY` so any running gateway instance refreshes its in-memory cache automatically.

### Product registration

Store the FinTS product key your bank association issued you:

```bash
gw-admin product update "<your-product-key>" --product-version "1.0.0"
```

This must be done before the gateway can start successfully. The key is loaded once at startup into memory — a restart is required to pick up a new key.

To verify both are in place:

```bash
gw-admin inspect state
```

---

## 5. Query the API

All banking endpoints are under `/v1/banking/` and require the API key in the `Authorization: Bearer <key>` header.

### List bank accounts

```bash
curl -s -X POST http://localhost:8000/v1/banking/accounts \
  -H "Authorization: Bearer <your-api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "protocol": "fints",
    "blz": "12345678",
    "user_id": "your-bank-login",
    "password": "your-bank-pin"
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
    "end_date": "2026-03-15"
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

### Handling pending TAN confirmation (decoupled TAN)

If your bank requires a TAN confirmation (e.g. SecureGo+ push), the response status is `202 Accepted` with an `operation_id`. Poll the status endpoint until it transitions to `completed` or `failed`:

```bash
curl -s http://localhost:8000/v1/banking/operations/<operation-id> \
  -H "Authorization: Bearer <your-api-key>" | jq
```

Pending operations expire after `GATEWAY_OPERATION_SESSION_TTL_SECONDS` (default 120 s).

### Liveness check (no auth required)

```bash
curl http://localhost:8000/health/live
# {"status":"ok"}
```
