# gateway-contracts

Shared code between the gateway HTTP service and the admin CLI. Both apps depend on this package; nothing else does.

## Contents

- `schema` — SQLAlchemy `Table` objects for the gateway database (consumers, institutes, product registrations). Also includes test helpers for spinning up an in-memory DB.
- `channels` — PostgreSQL NOTIFY channel name constants, so the gateway and the CLI agree on the same strings.
- `payloads` — typed dicts for NOTIFY payloads passed over those channels.

No business logic here — just the shared surface that lets the two apps talk to the same database and coordinate at runtime.

