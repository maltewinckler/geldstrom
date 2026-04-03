# geldstrom-cli

Fully AI generated. Developer CLI for manually testing the gateway API.
Useful for checking that a deployment is working without having to write any code.

## Commands

| Command | What it does |
|---------|--------------|
| `health` | Ping the gateway (no credentials needed) |
| `accounts` | List accounts for a given bank user |
| `balances` | Get account balances |
| `transactions` | Fetch transactions for an IBAN |
| `tan-methods` | Show available TAN methods |

All commands except `health` require bank credentials and a valid API key for the gateway.

## Setup

Copy `.env.example` to `.env` (or point `--env-file` at your own file) and fill in:

```
GATEWAY_URL=http://localhost:8000
GATEWAY_API_KEY=your-key
BLZ=12345678
USER_ID=your-bank-user
PASSWORD=your-pin
TAN_METHOD=946
```

Then run:

```
uv run geldstrom-cli accounts
```
