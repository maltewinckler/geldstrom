# gateway-admin-cli

Admin tool for managing the gateway database. Mostly useful for bootstrapping a fresh deployment or doing manual maintenance.

## What it does

- Register and revoke consumers (creates API keys stored in the DB)
- Load and refresh the FinTS institute catalog from the CSV in `data/`

## Usage

```sh
uv run gateway-admin-cli --help
```

Configuration is read from `../../config/admin_cli.env` (see the `.example` file next to it).

## Development

Run from the workspace root: `uv sync`, then `uv run pytest`, `uv run ruff`.
