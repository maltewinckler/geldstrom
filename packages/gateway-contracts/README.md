# gateway-contracts

Shared code between the gateway HTTP service and the admin CLI. Both apps depend on this package; nothing else should.

## Contents

### `schema`

SQLAlchemy `Table` objects for the three gateway database tables:

| Table | Description |
|-------|-------------|
| `api_consumers` | API consumers with Argon2id-hashed keys and status |
| `fints_institutes` | FinTS institute catalog (BLZ → BIC, name, PIN-TAN URL, …) |
| `fints_product_registration` | Singleton row holding the FinTS product key and version |

The module also exports `create_test_schema` / `drop_test_schema` helpers for spinning up an in-memory (or testcontainer) database in tests.

### `channels`

PostgreSQL NOTIFY channel name constants so the gateway and the CLI always agree on the same strings:

| Constant | Channel | Triggered by |
|----------|---------|--------------|
| `CONSUMER_UPDATED_CHANNEL` | `gw.consumer_updated` | Create / update / disable / rotate user |
| `CATALOG_REPLACED_CHANNEL` | `gw.catalog_replaced` | `catalog sync` |
| `PRODUCT_REGISTRATION_UPDATED_CHANNEL` | `gw.product_registration_updated` | `product update` |

### `payloads`

Typed dataclasses for the JSON payloads sent over those NOTIFY channels. Currently only `ConsumerUpdatedPayload` is used (carries `consumer_id`); catalog and product updates use no payload body.
