# geldstrom-cli

Developer CLI for manually exercising the gateway API. Useful for checking that a deployment is working without writing any code. Fully handles the decoupled TAN (2FA) polling loop — if your bank requires app approval, just tap "Confirm" on your phone and the CLI waits.

## Commands

| Command | Description |
|---------|-------------|
| `health` | Ping the gateway liveness endpoint (no credentials needed) |
| `accounts` | List bank accounts for a given user |
| `balances` | Fetch account balances |
| `transactions [--iban …] [--start …] [--end …]` | Fetch transaction history for an IBAN |
| `tan-methods` | Show TAN methods advertised by the bank |

All commands except `health` require bank credentials and a valid gateway API key.

## Setup

Copy `.env.example` to `.env` (or point `--env-file` at any file) and fill in:

```dotenv
GATEWAY_URL=http://localhost:8000
GATEWAY_API_KEY=your-key
BLZ=12345678
USER_ID=your-bank-user
PASSWORD=your-pin
TAN_METHOD=946       # e.g. 946 for SecureGo+ / decoupled TAN
TAN_MEDIUM=          # optional: TAN device name (e.g. "SecureGo+")
```

Then run:

```sh
uv run geldstrom-cli accounts
uv run geldstrom-cli transactions --iban DE89370400440532013000 --start 2026-01-01
```

## CLI reference flags

Every command accepts `--env-file`, `--gateway-url`, `--api-key`, `--blz`, `--user-id`, `--password`, `--tan-method`, and `--tan-medium` as overrides for the corresponding env-file values.

## 2FA handling

If the bank responds with `202 Accepted`, the CLI prints the operation ID and polls every 2 seconds until the operation completes, fails, or expires. No extra steps needed — just approve on your device.
