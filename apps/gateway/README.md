# gateway

The main HTTP service. Handles API key authentication, proxies banking operations to the `geldstrom` package,
and manages decoupled TAN sessions in the background.

## What it does

- Accepts bank credentials from consumers (BLZ / user ID / PIN) and returns account data, balances, or transactions
- Responds synchronously (200) when the bank answers quickly, or asynchronously (202 + polling) when a 2FA step is needed
- Stores consumers and institutes in PostgreSQL; keeps sessions in an in-memory cache
- Emits LISTEN/NOTIFY events on the `gateway-contracts` channels so the admin CLI can react

## Endpoints

| Method | Path | What it does |
|--------|------|--------------|
| GET | `/health/live` | Liveness ping |
| GET | `/health/ready` | Readiness — checks DB + product key + institute catalog |
| POST | `/v1/banking/accounts` | List accounts |
| POST | `/v1/banking/balances` | Get balances |
| POST | `/v1/banking/transactions` | Fetch transactions |
| POST | `/v1/banking/tan-methods` | List available TAN methods |
| GET | `/v1/banking/operations/{id}` | Poll a pending 2FA operation |

All `/v1/banking/*` routes require a `Bearer` token in the `Authorization` header.

## Configuration

Copy `/config/gateway.env.example` to `/config/gateway.env` and fill in the values. The relevant settings live in `gateway/config.py`.
