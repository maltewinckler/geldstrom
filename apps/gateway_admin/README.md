# gateway-admin-cli

Admin tool for operating the gateway database. Handles first-run initialization, institute catalog management, product key registration, and API consumer lifecycle. Available as a standalone binary (`gw-admin`) or as a Docker one-shot container.

## Command reference

### `gw-admin db`

| Command | Description |
|---------|-------------|
| `db init` | Create the database, tables, and restricted gateway DB user (idempotent). Also applies the FinTS product registration key from the env file. |

### `gw-admin users`

| Command | Description |
|---------|-------------|
| `users list` | List all API consumers |
| `users create <email>` | Create a new consumer; prints the raw API key **once** |
| `users update <id> --email <new>` | Update a consumer's email |
| `users disable <id>` | Disable a consumer (key stops working) |
| `users reactivate <id>` | Re-enable a disabled consumer |
| `users rotate <id>` | Issue a new API key; old key is invalidated immediately |
| `users delete <id> --confirm` | Permanently delete a consumer |

### `gw-admin catalog`

| Command | Description |
|---------|-------------|
| `catalog sync <csv-path>` | Replace the institute catalog from a Bundesbank CSV (idempotent; fires `gw.catalog_replaced` NOTIFY) |

### `gw-admin product`

| Command | Description |
|---------|-------------|
| `product update <key> --product-version <ver>` | Store or replace the FinTS product registration key |

### `gw-admin inspect`

| Command | Description |
|---------|-------------|
| `inspect state [--blz <blz>]` | Print DB connectivity, user count, institute count, and product registration status. Pass `--blz` to look up a specific institute. |

## Configuration

Copy `config/admin_cli.env.example` to `config/admin_cli.env` and fill in the values. The CLI uses two sets of credentials:

- **PostgreSQL superuser** (`POSTGRES_USER` / `POSTGRES_PASSWORD`) — needed by `db init` to create the database and the restricted gateway user.
- **Gateway DB user** (`GATEWAY_DB_USER` / `GATEWAY_DB_PASSWORD`) — used for all other operations (same user that the gateway service connects as).

The FinTS product key can be pre-seeded via `FINTS_PRODUCT_REGISTRATION_KEY` in the env file — `db init` will apply it automatically.

## Usage

```sh
# Local (in the workspace, with uv)
uv run gw-admin --help

# Docker one-shot
docker compose run --rm gateway-admin-cli gw-admin db init
docker compose run --rm gateway-admin-cli gw-admin catalog sync /data/fints_institute.csv
docker compose run --rm gateway-admin-cli gw-admin users create you@example.com
```