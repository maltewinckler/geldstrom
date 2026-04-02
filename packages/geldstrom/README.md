# geldstrom

Pure-Python FinTS 3.0 client for German banking. Handles the protocol layer (parsing, serialization, dialog management) and exposes a clean async API for fetching accounts, balances, and transactions.

## What's in here

- `clients/` — the main entry point (`FinTS3Client`)
- `domain/` — models and port definitions
- `infrastructure/fints/` — protocol implementation: tokenizer, parser, segment models, dialogs, operations

## Usage

```python
from geldstrom import FinTS3Client

async with FinTS3Client(blz="12345678", user_id="...", pin="...") as client:
    accounts = await client.get_accounts()
```

Some operations (e.g. fetching transactions for decoupled TAN banks) require handling a 2FA challenge. See the `examples/` directory in the repo root for runnable demos.
