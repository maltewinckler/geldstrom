# gateway-contracts

Shared database schema and channel contracts for the Geldstrom gateway.

This package contains the **only** code shared between the HTTP API gateway and the
admin CLI tool:

- `schema` — SQLAlchemy `Table` definitions and test helpers
- `channels` — PostgreSQL NOTIFY channel name constants
- `product_key` — Fernet-based product key encryption/decryption service
