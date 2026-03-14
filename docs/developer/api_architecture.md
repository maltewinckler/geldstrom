# Gateway API Architecture

## Purpose

This document defines the target architecture for a new gateway API under `apps/` that allows third-party products to use:

1. The Geldstrom FinTS integration capabilities
2. The maintained FinTS institute catalog from `data/fints_institute.csv`
3. A shared FinTS product registration key managed by the platform

The gateway must be:

- secure by default
- fast on the request path
- maintainable over time
- aligned with Domain-Driven Design (DDD)
- explicit about where state lives and where it must never live

This is an architecture plan, not an implementation guide.

## Critical Architectural Clarification

The requested deployment can be made **non-retentive for customer banking secrets**, but not literally zero knowledge in the cryptographic sense.

Reason:

- the backend must temporarily see the bank username and bank password in order to talk to the bank
- therefore the backend process has transient access to the secrets in memory during request execution

The correct architectural goal is therefore:

**Non-retentive secret handling**

This means:

- bank credentials are accepted only for the lifetime of a request
- they are never persisted
- they are never cached
- they are never logged
- they are never included in traces, metrics labels, events, or exception text

The same standard applies to IBAN and API keys on the request path.

## Architectural Principles

The gateway app must follow these principles.

### 1. Pure domain core

The domain layer must not know about:

- FastAPI
- PostgreSQL
- SQLAlchemy
- Redis
- Geldstrom infrastructure classes
- logging frameworks
- environment variables

The domain only knows:

- business concepts
- invariants
- repository interfaces
- domain services
- value objects

### 2. Clear bounded contexts

The gateway app is not one undifferentiated service. It contains four clear business areas.

1. `consumer_access`
2. `institution_catalog`
3. `product_registration`
4. `banking_gateway`

The bank interaction flow is mostly **application orchestration plus an anti-corruption layer** over the existing Geldstrom package rather than a persistence-heavy domain.

Decoupled 2FA also introduces an additional runtime concern:

5. `operation_sessions`

This is not a repository-backed business context. It is an ephemeral runtime concern for pending bank operations waiting for confirmation in a banking app.

### 3. State separation

Stateful and stateless concepts must be separated explicitly.

Stateful:

- API consumer accounts
- API key hashes
- institution catalog rows
- product registration secret record
- in-memory caches
- in-memory pending operation sessions

Stateless:

- authentication policy
- request authorization policy
- bank operation orchestration
- response mapping
- health evaluation rules

### 4. Dependency inversion everywhere

Application services depend on:

- repository ports
- cache ports
- banking connector ports
- time and id providers
- secret protection services

Infrastructure provides the implementations.

### 5. No persistence of customer banking data

The gateway must never persist:

- bank username
- bank password
- TAN responses
- fetched account data
- fetched transaction data
- bank session tokens
- raw request bodies containing secrets

If future product requirements demand persistence of fetched banking data, that must be designed as a separate bounded context with explicit consent, encryption, retention policies, and legal review. It is out of scope for this architecture.

## Recommended Monorepo Placement

Recommended monorepo placement:

```text
apps/
├── gateway/
└── gateway_admin_cli/
```

Recommended roles:

- `gateway`: single gateway service app containing HTTP presentation, domain, application, and infrastructure
- `gateway_admin_cli`: CLI presentation app for administration and maintenance

Recommended internal package boundaries:

```text
apps/gateway/gateway/
apps/gateway_admin_cli/gateway_admin_cli/
```

The backend core should depend on the workspace package `geldstrom`, but it must wrap it behind its own interface boundary.

The admin CLI should depend on `gateway`. The HTTP API lives inside `gateway` itself.

This is the cleanest way to keep the admin layer fully decoupled while avoiding duplication and avoiding local HTTP round-trips inside the same container.

## Administrative Interface Position

Yes, a dedicated admin CLI makes sense.

It should be modeled as a **separate presentation app**, not as part of the HTTP API presentation layer.

That means:

- the admin CLI is not implemented as extra HTTP routes
- the admin CLI is not implemented by shelling out into the API process
- the admin CLI is not implemented as a client that calls `localhost` HTTP endpoints inside the same container

Instead, both presentation apps should call the same backend application services directly through their own composition roots.

This preserves clear communication boundaries:

- HTTP API for product consumers
- CLI for operators and administrators

while still sharing one backend core with one domain model and one set of use cases.

## Bounded Contexts

### 1. Consumer Access Context

Responsibility:

- model API consumers
- store and verify API keys
- expose the authenticated platform identity to application use cases

Core rules:

- API keys are never stored in plaintext
- only a one-way hash is stored
- the presented API key is verified in memory against the stored hash
- the raw API key is only returned once at creation time

Primary aggregate:

- `ApiConsumer`

### 2. Institution Catalog Context

Responsibility:

- persist and serve the FinTS institute catalog derived from `fints_institute.csv`
- provide fast lookup by BLZ
- expose only the operationally relevant fields to the rest of the app

Core rules:

- the CSV should not be modeled as a giant anemic row object with every source column forced into the core domain
- the domain should model only the fields needed by the gateway
- the original source row can still be retained as raw metadata for traceability

Primary aggregate:

- `FinTSInstitute`

### 3. Product Registration Context

Responsibility:

- hold the shared FinTS product registration secret used by the gateway
- expose it securely to the banking connector

Core rules:

- this secret must not be stored as plaintext in PostgreSQL
- it should be encrypted at the application boundary before persistence
- it should be loaded into memory once at startup and refreshed only on change

Primary aggregate:

- `FinTSProductRegistration`

### 4. Banking Gateway Context

Responsibility:

- execute bank operations on behalf of an authenticated API consumer
- coordinate institute lookup, product registration lookup, and live bank access
- select the requested protocol from the API contract
- map request DTOs to the Geldstrom anti-corruption layer

This context should remain mostly stateless and orchestration-focused.

It should not persist customer banking state.

### 5. Operation Session Runtime Context

Responsibility:

- hold pending decoupled-authentication operations in memory
- resume them without blocking request threads
- expose operation state to follow-up API calls

Core rules:

- sessions are ephemeral and must never be persisted to PostgreSQL
- sessions may contain bank session state and therefore must be treated as sensitive runtime data
- session entries must expire aggressively
- session entries must never contain raw bank passwords after the initial bank session has been established

This context belongs to runtime infrastructure and application orchestration, not to the long-lived business system of record.

## High-Level System View

```text
Client Application
	|
	| HTTPS + X-API-Key
	v
Gateway API
	|
	+--> Consumer Access Cache ----> Consumer Access Repository ----> PostgreSQL
	|
	+--> Institute Catalog Cache ---> Institute Repository ---------> PostgreSQL
	|
	+--> Product Config Cache ------> Product Repository ----------> PostgreSQL
	|
	+--> Operation Session Cache ---> Async Resume Worker
	|
	+--> Banking Connector Port ----> Protocol Adapter ------------> Banks
```

The PostgreSQL database is not on the hot path for most read requests after startup cache warmup.

## Application Capabilities

The public API should support these business operations.

1. `ListAccounts`
2. `FetchHistoricalTransactions`
3. `GetAllowedTanMethods`
4. `HealthCheck`
5. `GetOperationStatus`

All banking operations require:

- `X-API-Key` header
- protocol
- bank username
- bank password
- bank identifier (BLZ)

Transaction history additionally requires:

- account IBAN

For the first implementation, the only supported value of `protocol` is `fints`.

The contract must still include the protocol field now so that later protocols can be added without changing the public API shape.

## Public API Shape

Use `POST` for operations that require secrets. Do not put secrets in query strings or path parameters.

Recommended endpoints:

```text
GET  /health/live
GET  /health/ready

POST /v1/banking/accounts
POST /v1/banking/transactions
POST /v1/banking/tan-methods
GET  /v1/banking/operations/{operation_id}
```

Rationale:

- `GET` is appropriate for health because no secrets are submitted
- `POST` is required for bank operations because request bodies contain secrets
- even TAN-method lookup should be `POST`, because credentials may be needed and must not appear in URLs or access logs
- `GET /v1/banking/operations/{operation_id}` is safe because it operates on a gateway-issued opaque identifier and does not require resubmitting bank credentials

## Asynchronous Decoupled 2FA Contract

The gateway only supports **decoupled 2FA methods**.

That means:

- the user starts an operation through the gateway API
- the bank requires confirmation in the user’s banking app
- the gateway stores the pending bank session in an in-memory session cache
- the gateway returns immediately with an operation identifier
- the gateway resumes the operation asynchronously until the bank confirms completion or the operation expires

This keeps request handlers non-blocking at the business level and prevents workers from waiting on a human approval step.

### Required response model for decoupled flows

When an operation requires app approval, the gateway should return a pending result such as:

```json
{
	"status": "pending_confirmation",
	"operation_id": "op_...",
	"protocol": "fints",
	"confirmation_type": "decoupled",
	"expires_at": "..."
}
```

When an operation completes, the status endpoint should return either:

- `completed`
- `failed`
- `expired`

with the final business payload attached only in the completed case.

## Request and Response Contracts

### Common request contract requirements

All secret-bearing fields should use `pydantic.SecretStr` from the presentation layer inward.

That includes application DTOs and gateway-owned domain value objects where keeping the secret wrapped is preferable to converting it to plaintext too early.

Example conceptual request model:

```python
class BankAccessRequest(BaseModel):
	protocol: Literal["fints"]
	bank_identifier: str
	bank_username: SecretStr
	bank_password: SecretStr
```

Extended transaction request:

```python
class TransactionHistoryRequest(BankAccessRequest):
	iban: SecretStr
	start_date: date | None = None
	end_date: date | None = None
```

Even though an IBAN is not as sensitive as a password, this API should treat it as sensitive because it directly identifies a customer account.

### Protocol field rules

The protocol field is mandatory in the external contract.

Rules:

- it is part of every banking request
- it selects the banking connector implementation
- it prevents hard lock-in to FinTS at the contract level
- the first released value is `fints`

Recommended domain value object:

- `BankProtocol`

Recommended external schema type:

- enum with `fints` as the initial member

### Response design

Responses must be plain business DTOs with no infrastructure-specific detail.

Do not leak:

- internal exception types
- raw FinTS segment data
- bank server URLs unless explicitly intended
- source CSV internals unless necessary

## HTTP API Specification

This section defines the concrete HTTP contract that the first gateway release should expose.

It is intentionally close to an OpenAPI document, but remains embedded in this architecture plan until implementation starts.

### API metadata

- title: `Geldstrom Gateway API`
- versioning strategy: URL versioning with `/v1`
- transport: HTTPS only
- media type: `application/json`
- authentication: `X-API-Key` header

### Security scheme

Every banking endpoint requires:

- header `X-API-Key: <api key>`
- header `Content-Type: application/json`
- header `Accept: application/json`

Optional but recommended headers:

- `X-Request-Id` supplied by the client for correlation

Gateway behavior:

- reject missing API keys with `401 Unauthorized`
- reject invalid API keys with `401 Unauthorized`
- reject disabled consumers with `403 Forbidden`
- echo `X-Request-Id` in the response if it was supplied
- generate a gateway request id when the client did not supply one

### Shared response headers

Recommended response headers for all endpoints:

- `Content-Type: application/json`
- `X-Request-Id: <request id>`
- `Cache-Control: no-store` for all banking endpoints

Health endpoints may use less restrictive cache headers if operationally useful, but the default should still be conservative.

### Shared schema components

#### `BankProtocol`

```json
{
	"type": "string",
	"enum": ["fints"]
}
```

#### `BankAccessRequest`

```json
{
	"type": "object",
	"required": [
		"protocol",
		"bank_identifier",
		"bank_username",
		"bank_password"
	],
	"properties": {
		"protocol": {
			"type": "string",
			"enum": ["fints"]
		},
		"bank_identifier": {
			"type": "string",
			"description": "Bank routing identifier, initially the German BLZ."
		},
		"bank_username": {
			"type": "string",
			"writeOnly": true
		},
		"bank_password": {
			"type": "string",
			"writeOnly": true
		}
	},
	"additionalProperties": false
}
```

#### `TransactionHistoryRequest`

Note: this schema is written as a flat object rather than using `allOf` composition.
Using `allOf` together with `additionalProperties: false` in separate subschemas produces
validation failures in strict validators because each subschema evaluates `additionalProperties`
against only the properties declared in that subschema. A flat listing is unambiguous.

```json
{
	"type": "object",
	"required": [
		"protocol",
		"bank_identifier",
		"bank_username",
		"bank_password",
		"iban"
	],
	"properties": {
		"protocol": {
			"type": "string",
			"enum": ["fints"]
		},
		"bank_identifier": {
			"type": "string",
			"description": "Bank routing identifier, initially the German BLZ."
		},
		"bank_username": {
			"type": "string",
			"writeOnly": true
		},
		"bank_password": {
			"type": "string",
			"writeOnly": true
		},
		"iban": {
			"type": "string",
			"writeOnly": true
		},
		"start_date": {
			"type": "string",
			"format": "date"
		},
		"end_date": {
			"type": "string",
			"format": "date"
		}
	},
	"additionalProperties": false
}
```

#### `PendingOperationResponse`

```json
{
	"type": "object",
	"required": [
		"status",
		"operation_id",
		"protocol",
		"confirmation_type",
		"expires_at",
		"polling_interval_seconds"
	],
	"properties": {
		"status": {
			"type": "string",
			"enum": ["pending_confirmation"]
		},
		"operation_id": {
			"type": "string"
		},
		"protocol": {
			"$ref": "#/components/schemas/BankProtocol"
		},
		"confirmation_type": {
			"type": "string",
			"enum": ["decoupled"]
		},
		"expires_at": {
			"type": "string",
			"format": "date-time"
		},
		"polling_interval_seconds": {
			"type": "integer",
			"description": "Recommended minimum polling interval. Clients must not poll more frequently than this value."
		}
	},
	"additionalProperties": false
}
```

#### `ErrorResponse`

```json
{
	"type": "object",
	"required": ["error"],
	"properties": {
		"error": {
			"type": "object",
			"required": ["code", "message", "request_id"],
			"properties": {
				"code": {
					"type": "string"
				},
				"message": {
					"type": "string"
				},
				"request_id": {
					"type": "string"
				},
				"details": {
					"type": "object"
				}
			}
		}
	},
	"additionalProperties": false
}
```

Recommended stable error codes:

- `unauthorized`
- `forbidden`
- `validation_error`
- `unsupported_protocol`
- `institution_not_found`
- `bank_authentication_failed`
- `decoupled_confirmation_required`
- `operation_not_found`
- `operation_expired`
- `bank_upstream_unavailable`
- `internal_error`

### Endpoint specification

#### `GET /health/live`

Purpose:

- liveness probe for process supervision

Authentication:

- none

Response `200 OK`:

```json
{
	"status": "ok"
}
```

#### `GET /health/ready`

Purpose:

- readiness probe for traffic admission

Authentication:

- none

Response `200 OK`:

```json
{
	"status": "ready",
	"checks": {
		"postgres": "ok",
		"consumer_cache": "ok",
		"institute_cache": "ok",
		"product_registration_cache": "ok",
		"product_key_material": "ok",
		"operation_session_runtime": "ok"
	}
}
```

Response `503 Service Unavailable`:

```json
{
	"status": "not_ready",
	"checks": {
		"postgres": "failed"
	}
}
```

#### `POST /v1/banking/accounts`

Purpose:

- list visible accounts for the supplied bank access

Authentication:

- required via `X-API-Key`

Request body:

- `BankAccessRequest`

Successful synchronous response `200 OK`:

```json
{
	"status": "completed",
	"protocol": "fints",
	"accounts": [
		{
			"account_id": "DE02120300000000202051-0",
			"iban": "DE02120300000000202051",
			"name": "Girokonto",
			"currency": "EUR",
			"account_type": "checking"
		}
	]
}
```

Note: `account_id` and `iban` are passed through from the banking protocol response as-is. The gateway does not generate or transform these identifiers. Format varies by bank and protocol.

Pending decoupled response `202 Accepted`:

- `PendingOperationResponse`

Error responses:

- `400 Bad Request` for malformed JSON or invalid fields
- `401 Unauthorized` for missing or invalid API key
- `403 Forbidden` for disabled consumer
- `404 Not Found` when the bank identifier is unknown in the institute catalog
- `422 Unprocessable Entity` when bank credentials are rejected or request dates are invalid
- `424 Failed Dependency` when the bank upstream is reachable but cannot complete the requested operation
- `502 Bad Gateway` when upstream bank behavior is invalid or unusable
- `503 Service Unavailable` when required internal dependencies are unavailable

#### `POST /v1/banking/transactions`

Purpose:

- fetch historical transactions for one account

Authentication:

- required via `X-API-Key`

Request body:

- `TransactionHistoryRequest`

Successful synchronous response `200 OK`:

```json
{
	"status": "completed",
	"protocol": "fints",
	"account": {
		"iban": "DE02120300000000202051"
	},
	"transactions": [
		{
			"transaction_id": "2026-03-05-0001",
			"booking_date": "2026-03-05",
			"value_date": "2026-03-05",
			"amount": "-24.95",
			"currency": "EUR",
			"credit_debit": "debit",
			"counterparty_name": "Example Merchant",
			"remittance_information": "Card payment"
		}
	]
}
```

Note: `transaction_id` is passed through from the banking protocol response. The gateway does not generate or deduplicate transaction identifiers. Deduplication is out of scope for v1.

Pending decoupled response `202 Accepted`:

- `PendingOperationResponse`

Additional validation rules:

- `start_date` must be less than or equal to `end_date` when both are present
- if no date range is supplied, the application layer defaults to the 90 days prior to today as `start_date` and today as `end_date`
- pagination is optional for the first release and may be omitted if the underlying banking flow does not support stable cursors yet

#### `POST /v1/banking/tan-methods`

Purpose:

- return the decoupled confirmation methods that are currently usable for the bank access

Authentication:

- required via `X-API-Key`

Request body:

- `BankAccessRequest`

Successful synchronous response `200 OK`:

```json
{
	"status": "completed",
	"protocol": "fints",
	"tan_methods": [
		{
			"method_id": "942",
			"display_name": "App-Freigabe",
			"confirmation_type": "decoupled"
		}
	]
}
```

Pending decoupled response `202 Accepted`:

- `PendingOperationResponse`

Contract rule:

- only methods compatible with decoupled approval may be returned
- SMS, chipTAN, photoTAN, or other interactive challenge entry methods must be filtered out of the public response

#### `GET /v1/banking/operations/{operation_id}`

Purpose:

- inspect the state of a previously accepted pending operation

Authentication:

- required via `X-API-Key`

Path parameters:

- `operation_id`: opaque gateway-generated identifier

Response `200 OK` while pending:

```json
{
	"status": "pending_confirmation",
	"operation_id": "op_123",
	"protocol": "fints",
	"confirmation_type": "decoupled",
	"expires_at": "2026-03-07T12:15:00Z",
	"polling_interval_seconds": 3
}
```

Response `200 OK` when completed with accounts payload:

```json
{
	"status": "completed",
	"operation_id": "op_123",
	"protocol": "fints",
	"result_type": "accounts",
	"result": {
		"accounts": [
			{
				"account_id": "DE02120300000000202051-0",
				"iban": "DE02120300000000202051",
				"name": "Girokonto",
				"currency": "EUR",
				"account_type": "checking"
			}
		]
	}
}
```

Response `200 OK` when completed with transactions payload:

```json
{
	"status": "completed",
	"operation_id": "op_123",
	"protocol": "fints",
	"result_type": "transactions",
	"result": {
		"account": {
			"iban": "DE02120300000000202051"
		},
		"transactions": [
			{
				"transaction_id": "2026-03-05-0001",
				"booking_date": "2026-03-05",
				"value_date": "2026-03-05",
				"amount": "-24.95",
				"currency": "EUR",
				"credit_debit": "debit",
				"counterparty_name": "Example Merchant",
				"remittance_information": "Card payment"
			}
		]
	}
}
```

Response `200 OK` when completed with tan_methods payload:

```json
{
	"status": "completed",
	"operation_id": "op_123",
	"protocol": "fints",
	"result_type": "tan_methods",
	"result": {
		"tan_methods": [
			{
				"method_id": "942",
				"display_name": "App-Freigabe",
				"confirmation_type": "decoupled"
			}
		]
	}
}
```

The `result_type` field discriminates the shape of `result`. All three variants share the same outer envelope. Clients must use `result_type` to deserialize `result` correctly.

Response `200 OK` when failed:

```json
{
	"status": "failed",
	"operation_id": "op_123",
	"protocol": "fints",
	"error": {
		"code": "bank_authentication_failed",
		"message": "The bank rejected the submitted credentials.",
		"request_id": "req_123"
	}
}
```

Response `200 OK` when expired:

```json
{
	"status": "expired",
	"operation_id": "op_123",
	"protocol": "fints",
	"expired_at": "2026-03-07T12:15:00Z"
}
```

Response `404 Not Found`:

- returned when the operation id is unknown, belongs to another consumer, or has already been purged from the in-memory runtime store

### Status code policy

Recommended mapping:

- `200 OK`: request completed immediately or operation status fetched successfully
- `202 Accepted`: request accepted and waiting for decoupled user confirmation
- `400 Bad Request`: malformed JSON, unsupported body shape, or invalid primitive formatting
- `401 Unauthorized`: missing or invalid API key
- `403 Forbidden`: authenticated consumer is disabled or not allowed to inspect the resource
- `404 Not Found`: institute or operation not found
- `409 Conflict`: operation state does not allow the requested transition if future mutating status endpoints are introduced
- `422 Unprocessable Entity`: semantically invalid request or rejected bank credentials
- `424 Failed Dependency`: bank or protocol adapter cannot complete an otherwise valid request
- `429 Too Many Requests`: consumer-level rate limit exceeded
- `500 Internal Server Error`: unexpected internal failure
- `502 Bad Gateway`: invalid upstream bank response
- `503 Service Unavailable`: required gateway dependency unavailable

### Error handling rules

- error bodies must use `ErrorResponse`
- plaintext secrets must never be copied into error messages or validation payloads
- upstream bank messages may be normalized before exposure to prevent leaking implementation detail or unsafe content
- `request_id` must always be present in error responses
- validation failures should identify offending fields, but must not echo secret values

### Idempotency and retries

For the first release:

- `GET` endpoints are naturally retryable
- banking `POST` endpoints may be retried by the client only when the previous attempt definitively failed before acceptance
- if a request has already returned `202 Accepted`, the client should switch to polling `GET /v1/banking/operations/{operation_id}` instead of resubmitting credentials

Future improvement:

- add optional `Idempotency-Key` support for banking `POST` endpoints once operation deduplication semantics are fully defined

## DDD Layering

Recommended package structure:

```text
apps/
├── gateway/
│   ├── pyproject.toml
│   ├── README.md
│   └── gateway/
│       ├── bootstrap/
│       │   ├── config.py
│       │   ├── container.py
│       │   ├── lifecycle.py
│       │   └── logging.py
│       ├── domain/
│       │   ├── shared/
│       │   ├── consumer_access/
│       │   ├── institution_catalog/
│       │   ├── product_registration/
│       │   └── banking_gateway/
│       ├── application/
│       │   ├── common/
│       │   ├── consumer_access/
│       │   ├── institution_catalog/
│       │   ├── product_registration/
│       │   ├── operation_sessions/
│       │   ├── banking_gateway/
│       │   └── administration/
│       ├── infrastructure/
│           ├── persistence/
│           │   └── postgres/
│           ├── cache/
│           │   └── memory/
│           ├── banking/
│           │   ├── protocols/
│           │   └── geldstrom/
│           ├── crypto/
│           └── observability/
│       └── presentation/
│           └── http/
│               ├── api.py
│               ├── dependencies.py
│               ├── middleware/
│               ├── routers/
│               └── schemas/
└── gateway_admin_cli/
    ├── pyproject.toml
    ├── README.md
    └── gateway_admin_cli/
        ├── bootstrap/
        └── presentation/
            └── cli/
                ├── main.py
                ├── commands/
                ├── formatters/
                └── prompts/
```

### Why this structure

It organizes the backend by business capability first, not by technical pattern alone.

That is the key DDD constraint here.

It also separates presentation concerns cleanly:

- HTTP transport lives only in `gateway/presentation/http/`
- CLI transport lives only in `gateway_admin_cli`
- business use cases live only in `gateway`

Bad structure for this app:

```text
models/
services/
repositories/
routers/
```

That shape becomes ambiguous and collapses multiple business concerns into one technical bucket.

## Domain Model

### Consumer Access Domain

#### Aggregate

`ApiConsumer`

Fields:

- `consumer_id`
- `email`
- `api_key_hash`
- `status`
- `created_at`
- `rotated_at`

Invariants:

- email is unique
- api key hash must exist for active consumers
- revoked consumers cannot authenticate

#### Value objects

- `ConsumerId`
- `EmailAddress`
- `ApiKeyHash`
- `ConsumerStatus`

#### Stateless domain services

- `ApiKeyVerifier`

This service receives a presented API key and a stored key hash and returns whether they match.

### Institution Catalog Domain

#### Aggregate

`FinTSInstitute`

Recommended operational fields:

- `blz`
- `bic`
- `name`
- `city`
- `organization`
- `pin_tan_url`
- `fints_version`
- `last_source_update`
- `source_row_checksum`
- `source_payload`

Rationale:

- `blz` is the main lookup key
- `pin_tan_url` is what the banking connector actually needs
- `source_payload` preserves traceability without forcing the domain to mirror the entire CSV column layout forever

#### Value objects

- `BankLeitzahl`
- `Bic`
- `InstituteEndpoint`
- `InstituteName`

#### Stateless domain services

- `InstituteSelectionPolicy`

This service resolves conflicts if the CSV contains multiple rows for the same BLZ. That already exists in the source file and must be treated as a domain problem, not an incidental parsing detail.

Recommended rule order:

1. prefer rows with a PIN/TAN URL
2. prefer the most recent source update
3. if still ambiguous, prefer a deterministic canonical row and expose duplicates in administration diagnostics

### Product Registration Domain

#### Aggregate

`FinTSProductRegistration`

Fields:

- `registration_id`
- `encrypted_product_key`
- `product_version`
- `key_version`
- `updated_at`

Important:

- the aggregate should not expose plaintext by default
- decryption should happen only in the application service or infrastructure secret provider that needs to talk to the bank

#### Value objects

- `EncryptedProductKey`
- `ProductVersion`
- `KeyVersion`

### Banking Gateway Domain

This domain should remain intentionally small and mostly transient.

#### Value objects

- `BankProtocol`
- `PresentedBankCredentials`
- `PresentedBankUserId`
- `PresentedBankPassword`
- `RequestedIban`
- `AuthenticatedConsumer`

These must be modeled as transient value objects and must never be part of a repository-backed aggregate.

#### Stateless domain services

- `BankRequestSanitizationPolicy`

#### Application-facing operation states

The banking gateway use cases should expose explicit operation states:

- `completed`
- `pending_confirmation`
- `failed`
- `expired`

No persistent aggregate is required here in v1.

That is deliberate. Creating a fake aggregate just to satisfy a pattern would be worse than not creating one.

### Operation Session Runtime Model

This is not a repository-backed aggregate.

It is a sensitive, ephemeral runtime state model owned by the application and infrastructure layers.

Recommended model:

- `PendingOperationSession`

Recommended fields:

- `operation_id`
- `consumer_id`
- `protocol`
- `operation_type`
- `session_state`
- `status`
- `created_at`
- `expires_at`
- `last_polled_at`
- `result_payload` when completed
- `failure_reason` when failed

## Repository Ports

Repository ports belong to the domain.

Recommended ports:

```text
ApiConsumerRepository
FinTSInstituteRepository
FinTSProductRegistrationRepository
OperationSessionStore
```

Recommended methods:

### ApiConsumerRepository

- `get_by_id(consumer_id)`
- `get_by_email(email)`
- `get_by_api_key_hash(hash)` is optional and usually unnecessary if the cache is authoritative
- `list_all_active()`
- `save(consumer)`

### FinTSInstituteRepository

- `get_by_blz(blz)`
- `list_all()`
- `replace_catalog(institutes)`

### FinTSProductRegistrationRepository

- `get_current()`
- `save_current(registration)`

### OperationSessionStore

- `create(session)`
- `get(operation_id)`
- `update(session)`
- `delete(operation_id)`
- `expire_stale(now)`

`replace_catalog` is preferable to piecemeal mutation for the institute CSV because the source is effectively a snapshot dataset.

`OperationSessionStore` is intentionally not a PostgreSQL repository. In v1 it is an in-memory runtime store.

## Banking Connector Port

The gateway app must not call Geldstrom client classes directly from its application services.

Instead define a port such as:

```text
BankingConnector
```

Responsibilities:

- list accounts using presented credentials
- fetch transactions using presented credentials and IBAN
- get supported TAN methods using presented credentials
- support asynchronous decoupled-authentication start and resume

Recommended protocol-aware abstraction:

```text
ProtocolBankingConnector
```

where the app selects the concrete connector by `BankProtocol`.

Infrastructure implementation:

```text
infrastructure/banking/geldstrom/GeldstromBankingConnector
```

Later protocols should be added as sibling implementations, not by modifying the public API contract.

This is the anti-corruption layer.

Its job is to translate between:

- gateway value objects and DTOs
- Geldstrom domain and client models

This preserves the gateway boundary even though both projects live in the same monorepo.

## Persistence Design

### PostgreSQL is the system of record for

- API consumers
- institute catalog
- encrypted product registration

### PostgreSQL is not the system of record for

- request secrets
- bank sessions
- accounts discovered from live bank calls
- transaction history fetched from banks
- pending decoupled-authentication operation sessions

## Recommended Database Schema

### Table: `api_consumers`

Columns:

- `consumer_id` UUID primary key
- `email` CITEXT unique not null
- `api_key_hash` TEXT not null
- `status` TEXT not null
- `created_at` TIMESTAMPTZ not null
- `rotated_at` TIMESTAMPTZ null

Notes:

- store a hash, not the plaintext API key
- hash should be produced with a password-grade algorithm such as Argon2id

Argon2id parameters:

- recommended minimum: time_cost=2, memory_cost=65536 (64 MiB), parallelism=2
- these parameters must be configurable, not hardcoded
- store the hash in PHC string format so parameters are self-describing and forward-compatible with future cost increases
- authentication throughput on the hot path is protected by the consumer cache; the Argon2id cost is paid at provisioning and rotation time, not on every request

Required PostgreSQL extension:

- `CREATE EXTENSION IF NOT EXISTS citext;` must be applied before running migrations
- this is typically included as the first migration file

Recommended indexes:

- `UNIQUE` on `email` is already the primary lookup index (from the column constraint)
- no secondary index on `api_key_hash` is required in v1 because authentication is performed by scanning the in-memory active-consumer cache and verifying Argon2id hashes there

### Table: `fints_institutes`

Columns:

- `blz` TEXT primary key
- `bic` TEXT null
- `name` TEXT not null
- `city` TEXT null
- `organization` TEXT null
- `pin_tan_url` TEXT null
- `fints_version` TEXT null
- `last_source_update` DATE null
- `source_row_checksum` TEXT not null
- `source_payload` JSONB not null

Decision:

- v1 stores exactly one canonical row per BLZ, making `blz` the natural primary key
- duplicate source rows are resolved by `InstituteSelectionPolicy` before ingestion
- no surrogate UUID primary key is needed; `blz` is stable and the main lookup key

Recommended indexes:

- the primary key on `blz` covers all lookup queries
- no secondary indexes are required for v1 since the catalog is fully loaded into memory at startup and queried only by BLZ

### Table: `product_registrations`

Columns:

- `registration_id` UUID primary key
- `encrypted_product_key` BYTEA or TEXT not null
- `product_version` TEXT not null
- `key_version` TEXT not null
- `updated_at` TIMESTAMPTZ not null

Notes:

- encrypt before writing to PostgreSQL
- the encryption key must not live in the database
- use an environment-provided master key or a KMS-backed envelope key

Encryption key rotation:

- if a flat master key is used, rotating it requires re-encrypting the `encrypted_product_key` value
- this can be executed as a one-time admin operation via `UpdateProductRegistration` while the gateway is quiesced or briefly write-paused
- to make future key rotation cheaper, use an envelope encryption scheme: encrypt the product key with a per-record data encryption key (DEK), then encrypt the DEK with the master key
- with envelope encryption, rotating the master key requires only re-encrypting the DEK, not the product key value itself
- document the chosen approach explicitly before implementation; this decision cannot easily be changed after the first deployment

Recommended indexes:

- no secondary indexes required; there is only one active registration and it is loaded into memory at startup

## CSV Ingestion Strategy

The institute CSV is reference data, not request data.

Recommended ingestion flow:

1. parse `data/fints_institute.csv`
2. normalize rows into `FinTSInstitute` domain objects
3. resolve duplicates by BLZ using the catalog policy
4. replace the persisted catalog snapshot in one transaction
5. warm the in-memory catalog cache from the stored canonical records

This should be executed by:

- startup bootstrap if the database is empty
- or an internal admin command / scheduled sync pipeline

Do not parse the CSV on every request.

## Caching Strategy

The cache is there to keep PostgreSQL off the hot path.

### In-memory caches required in v1

1. `ApiConsumerCache`
2. `FinTSInstituteCache`
3. `ProductRegistrationCache`
4. `OperationSessionCache`

### Cache loading rules

At startup:

1. load all active consumers into memory
2. load the canonical institute catalog into memory
3. load the current product registration into memory
4. initialize an empty operation session cache
5. only mark readiness as healthy once all mandatory caches are warm

### Cache ownership

Cache objects are stateful infrastructure components.

They do not belong in the domain.

### Operation session cache rules

`OperationSessionCache` is different from the other caches.

It is not a mirror of PostgreSQL state.

It is a sensitive runtime store for pending operations waiting for decoupled confirmation.

It should contain only what is necessary to resume the bank operation, for example:

- `operation_id`
- authenticated consumer id
- selected protocol
- operation type
- bank session state needed to resume
- sanitized operation metadata
- current state
- creation time
- expiry time

It must not contain:

- raw bank password after session establishment
- raw API key
- raw request body

### Operation session expiry

Pending sessions must expire automatically.

Recommended behavior:

- assign a strict TTL per session
- cap the total number of concurrent pending sessions per instance to prevent unbounded memory growth under load spikes
- recommended default maximum: 10,000 concurrent sessions per instance (configurable)
- when the cap is reached, reject new banking operations that would create a session with `503 Service Unavailable` until capacity is available
- run a background sweeper to remove expired sessions
- surface expired operations as `expired` through the status endpoint

### Multi-instance scalability concern

Per-instance memory caches introduce cross-instance invalidation problems.

Because the gateway is intended to scale horizontally, the architecture should include invalidation from the beginning.

Recommended v1 invalidation mechanism:

- write-through repositories update PostgreSQL first
- after commit, publish a small invalidation event using PostgreSQL `NOTIFY`
- each instance listens and refreshes the affected local cache segment

Recommended NOTIFY channel names and payload format:

- `gw.consumer_updated`: published after any consumer create, update, or disable/delete
  - payload: `{"consumer_id": "<uuid>"}`
  - receiving instance: evict and reload the named consumer from PostgreSQL
- `gw.catalog_replaced`: published after a full catalog replacement via `SyncInstituteCatalog`
  - payload: `{"replaced_at": "<iso8601>"}`
  - receiving instance: reload the entire institute catalog from PostgreSQL
- `gw.product_registration_updated`: published after `UpdateProductRegistration` completes
  - payload: `{"registration_id": "<uuid>"}`
  - receiving instance: reload and re-decrypt the product registration from PostgreSQL

Payloads must be valid JSON and must not contain secrets.

This avoids introducing Redis before it is justified.

For `OperationSessionCache`, invalidation is not the main issue. Routing is.

Because sessions live only in memory, a follow-up request for an operation must reach the same instance that owns that session unless a shared ephemeral store is introduced later.

That means v1 needs one of these deployment constraints:

1. sticky routing by operation id
2. an instance-local operation id that encodes the owning node and is routed accordingly
3. a later move to a shared ephemeral secure store if horizontal elasticity becomes more important than simplicity

This limitation must be explicit in the deployment architecture.

### What should not be cached in v1

- bank usernames
- bank passwords
- transaction responses
- account lists
- TAN challenges
- reusable bank session blobs outside pending decoupled operations

Caching live bank results may improve latency later, but it creates data sensitivity, staleness, and invalidation complexity immediately. It should not be part of the first version.

Pending operation sessions are the only exception, because they are not a performance cache. They are an execution-state cache required to support asynchronous decoupled 2FA.

## Security Architecture

### 1. Secret handling

All incoming sensitive fields must use `SecretStr`.

The app must:

- avoid calling `get_secret_value()` until immediately before bank invocation
- keep secret scope as small as possible
- never include secret values in exceptions

### 2. Logging policy

The default logging posture must be deny-by-default.

Allowed request log fields:

- correlation id
- route name
- HTTP method
- response status
- duration
- authenticated consumer id

Forbidden log fields:

- request body
- bank username
- bank password
- IBAN
- API key
- authorization headers
- SQL bind values containing secrets

Required safeguards:

- custom HTTP middleware that suppresses body logging
- structured logging with explicit allowlisted fields
- disabled SQLAlchemy parameter logging
- disabled or customized access logging if the web server would log headers or URLs with sensitive data

### 3. Persistence protection

Rules:

- API keys are stored as hashes
- product registration is stored encrypted
- user banking credentials are not stored at all

### 4. Error handling

Banking errors must be mapped to sanitized API errors.

The response should describe:

- invalid credentials
- unknown bank identifier
- upstream bank unavailable
- unsupported operation

It must not describe:

- raw secret-bearing input
- raw FinTS request payloads
- stack traces

### 5. Observability

Metrics and traces must follow the same secret policy.

Do not create labels or span attributes from:

- BLZ plus username combinations
- IBAN
- API key fragments

Safe dimensions:

- route
- operation type
- result class
- bank organization class if derived from catalog and non-sensitive

### 6. Rate limiting

Rate limiting must be applied per authenticated API consumer.

Recommended v1 approach:

- enforce in the HTTP layer after authentication has resolved the consumer identity
- in FastAPI, prefer an authenticated dependency or route-level guard over pre-auth middleware for this specific limit
- use a fixed window counter keyed by consumer id
- recommended default limit: 60 requests per minute per consumer (configurable)
- respond with `429 Too Many Requests` when the limit is exceeded
- include a `Retry-After` response header with the number of seconds until the window resets

Industry-standard posture:

- edge or load-balancer rate limits are still useful for coarse anonymous traffic protection
- consumer-specific limits belong inside the authenticated application layer unless identity is already established at the edge

Forbidden approaches:

- rate limiting by IP address alone (consumers may share NAT)
- rate limiting before consumer authentication (unauthenticated traffic must fail at auth first)

Future improvement:

- move rate limit counters to a shared store such as Redis to enforce limits correctly across all instances
- for v1 with sticky routing or a single instance this is not strictly required

## Dependency Injection and Composition Root

Each app should have its own composition root.

```text
gateway/bootstrap/container.py
gateway_admin_cli/bootstrap/container.py
```

### Chosen approach: manual wiring

No third-party dependency injection container is required.

For the HTTP portion of `gateway`, FastAPI's built-in `Depends` system is the DI mechanism:

- `gateway/bootstrap/container.py` defines factory functions that create and return fully-wired use case instances
- FastAPI router dependencies call these factory functions via `Depends`
- lifespan startup hooks in the factory module initialize caches, background workers, and database pools once; subsequent `Depends` calls receive the already-initialized singletons

For the CLI app (`gateway_admin_cli`), manual wiring is sufficient:

- `gateway_admin_cli/bootstrap/container.py` is a plain module that constructs all dependencies on demand when a command is invoked
- Typer commands call `container.build_<use_case>()` directly at the start of each command function
- no lifecycle management is required because CLI commands are short-lived processes

Rationale:

- FastAPI's `Depends` already solves the HTTP DI problem cleanly without a separate library
- Typer commands are single-shot process executions; a DI container's lifecycle management adds complexity without benefit
- both approaches remain fully testable by passing fake implementations directly to use case constructors in tests

Responsibilities:

- `gateway/bootstrap/container.py` defines functions and singletons for repositories, caches, crypto services, banking connector, and application use cases
- `gateway/presentation/http/` wires HTTP presentation dependencies onto those use cases via FastAPI `Depends`
- `gateway_admin_cli/bootstrap/container.py` builds use cases on demand for Typer commands

The rest of the codebase must not instantiate infrastructure ad hoc.

### Dependency graph

```text
HTTP Router
  -> Application Use Case
			-> Authentication Service
			-> Cache Port / Repository Port
			-> Operation Session Store
			-> Banking Connector Port
			-> Unit of Work or Transaction Boundary
```

The use case does not know whether the repository is PostgreSQL-backed, in-memory for tests, or something else.

## Application Use Cases

Recommended use cases in the application layer:

### `AuthenticateConsumer`

Input:

- presented API key

Output:

- authenticated consumer identity

Behavior:

- resolve consumer from cache
- if the consumer is not found in cache, fail closed with `401 Unauthorized`; do not fall through to PostgreSQL
- verify API key hash against the cached hash
- return a minimal authenticated identity object

Rationale for fail-closed cache miss:

- the consumer cache is considered authoritative for authentication decisions
- falling through to PostgreSQL on every cache miss would undermine the cache's role on the hot path and introduce latency under load
- new consumers become visible only after the cache is refreshed via the NOTIFY invalidation mechanism

### `ListAccounts`

Behavior:

1. authenticate API consumer
2. resolve protocol connector from request
3. resolve bank by BLZ from catalog cache
4. resolve product registration from cache
5. call banking connector
6. if decoupled confirmation is required, create operation session and return pending status
7. otherwise map result to response DTO

### `FetchHistoricalTransactions`

Behavior:

1. authenticate API consumer
2. resolve protocol connector from request
3. resolve bank by BLZ from catalog cache
4. resolve product registration from cache
5. call banking connector for the requested IBAN
6. if decoupled confirmation is required, create operation session and return pending status
7. otherwise map result to response DTO

### `GetAllowedTanMethods`

Behavior:

1. authenticate API consumer
2. resolve protocol connector from request
3. resolve bank by BLZ from catalog cache
4. resolve product registration from cache
5. call banking connector
6. if decoupled confirmation is required, create operation session and return pending status
7. filter returned methods to decoupled-compatible ones only
8. map remaining methods to response DTO

### `GetOperationStatus`

Behavior:

1. authenticate API consumer
2. load operation session from the operation session cache
3. verify that the operation belongs to the authenticated consumer
4. if operation is still pending, return the current state
5. if operation has completed, return the final payload and remove the session when appropriate
6. if operation has expired, return expired status and clean it up

### `ResumePendingOperations`

This is not a public endpoint. It is an internal background use case.

Behavior:

1. scan pending operation sessions
2. poll the selected banking connector for decoupled status
3. transition operations to completed, failed, or expired
4. update or remove the session entry

Behavior on process restart:

- pending sessions exist only in memory and are lost when the process terminates
- on restart, the in-memory session cache starts empty
- clients polling for a session that no longer exists will receive `404 Not Found`
- clients should treat `404` on a previously-accepted operation as equivalent to expiry
- clients should apply their own timeout that does not exceed the expected operation TTL to avoid polling indefinitely

### `EvaluateHealth`

Behavior:

- liveness checks process health only
- readiness checks DB connectivity, required caches, and crypto/material configuration availability

## Administration Use Cases

The admin CLI should drive dedicated application use cases in `gateway/application/administration/`.

Recommended use cases:

### `SyncInstituteCatalog`

Behavior:

1. read `data/fints_institute.csv`
2. normalize rows into domain objects
3. resolve duplicates according to `InstituteSelectionPolicy`
4. replace the canonical catalog in PostgreSQL
5. refresh the in-memory institute cache

### `CreateApiConsumer`

Behavior:

1. validate email and initial status
2. generate a new API key
3. hash the API key
4. persist the consumer
5. refresh the consumer cache
6. print the raw API key once to the operator

### `UpdateApiConsumer`

Behavior:

1. load consumer by id or email
2. update mutable operator-managed fields such as email or status metadata
3. persist the updated consumer
4. refresh the consumer cache

### `ListApiConsumers`

Behavior:

1. load consumers from PostgreSQL or a synchronized operator-facing read model
2. return only non-secret fields such as id, email, status, created_at, and rotated_at
3. never return API keys or any material derived from them

### `RotateApiConsumerKey`

Behavior:

1. load consumer by id or email
2. generate a replacement API key
3. hash and persist it
4. refresh the consumer cache
5. print the raw replacement key once

### `DisableApiConsumer`

Behavior:

1. load consumer
2. change status to revoked or disabled
3. persist the change
4. refresh the consumer cache

### `DeleteApiConsumer`

Behavior:

1. load consumer
2. apply deletion policy
3. remove the record or mark it deleted according to the chosen retention model
4. refresh the consumer cache

### `UpdateProductRegistration`

Behavior:

1. accept the new product key through a secret-safe CLI prompt
2. encrypt the value
3. persist it
4. refresh the product registration cache

### `InspectBackendState`

Behavior:

- display sanitized health and cache information for operators
- never display plaintext product keys
- never display raw API keys after initial creation or rotation

## Health Model

Recommended health endpoints:

### `GET /health/live`

Returns success if:

- process is running

It should not depend on database or external bank availability.

### `GET /health/ready`

Returns success only if:

- PostgreSQL is reachable
- consumer cache is warm
- institute cache is warm
- product registration cache is warm
- operation session runtime is initialized
- product decryption material is available

Bank upstream availability should not be part of readiness, because banks are external dependencies with varying uptime and the gateway should remain deployable even if one bank is down.

## Administrative CLI

The administrative interface should be implemented as a separate CLI presentation app.

Recommended command areas:

- `institutes sync`
- `institutes inspect`
- `consumers create`
- `consumers list`
- `consumers update`
- `consumers disable`
- `consumers delete`
- `consumers rotate-key`
- `product-key update`
- `health inspect`

Recommended CLI design rules:

- commands call backend application use cases directly
- secret inputs use non-echoing prompts
- command output is sanitized by default
- machine-readable output should be available with a structured flag such as JSON
- destructive commands should require explicit confirmation unless `--yes` is provided

The CLI is a presentation layer, not an infrastructure script bundle.

That means:

- no direct SQL in CLI commands
- no ad hoc CSV rewriting in CLI commands outside application services
- no bypassing repositories or caches just because the tool is internal

## Anti-Corruption Layer to Geldstrom

The existing `geldstrom` package already has a strong DDD structure. That is good, but the gateway must still keep its own boundary.

The gateway must not let:

- HTTP schemas
- cache entities
- SQLAlchemy rows

flow directly into Geldstrom client calls.

Instead:

1. gateway application assembles a transient banking command
2. anti-corruption adapter maps it to Geldstrom inputs
3. Geldstrom returns domain results
4. adapter maps them back to gateway response DTOs

For decoupled flows, the adapter must also map Geldstrom session state into a gateway-owned pending operation session model that can be resumed asynchronously.

This keeps the app readable and prevents cross-layer leakage.

### Exception mapping

The anti-corruption adapter is responsible for catching all Geldstrom exceptions and translating them into gateway domain errors before they cross into the application layer.

Geldstrom exception types must never appear in gateway application or presentation code.

Recommended initial mapping:

| Situation                                          | Gateway error code                 | HTTP status |
|----------------------------------------------------|------------------------------------|-------------|
| Bank rejects credentials                           | `bank_authentication_failed`       | 422         |
| BLZ has no usable PIN/TAN URL                      | `institution_not_found`            | 404         |
| Bank requires decoupled app confirmation           | _(creates pending session)_        | 202         |
| Bank session error or protocol fault               | `bank_upstream_unavailable`        | 502         |
| Operation not supported by this bank               | `bank_upstream_unavailable`        | 424         |
| Network timeout or connection failure              | `bank_upstream_unavailable`        | 502         |
| Unsupported protocol value                         | `unsupported_protocol`             | 400         |
| Unclassified / unexpected Geldstrom exception      | `internal_error`                   | 500         |

Rules:

- exception messages from Geldstrom must not be forwarded to the API response
- exceptions may be logged at error level after stripping any secret-bearing fields
- the adapter must not silently swallow exceptions; all unclassified cases must surface as `internal_error`

## Runtime Request Flow

```text
HTTP request
  -> presentation schema validation
  -> authenticate API key from consumer cache
	-> resolve protocol from request
  -> resolve BLZ from institute cache
  -> resolve product config from product cache
  -> create transient bank credentials value object
  -> invoke banking connector
	-> if decoupled confirmation is required, write operation session to in-memory cache and return operation id
	-> otherwise map result to response DTO
  -> dispose of transient secret-bearing objects
```

No PostgreSQL reads are required on the normal read path after startup warmup unless the cache is cold or invalidated.

## Startup Flow

```text
Process start
  -> load settings
  -> initialize structured logging
  -> initialize PostgreSQL connection pool
  -> initialize repositories
  -> initialize crypto service
  -> warm institute cache
  -> warm product registration cache
  -> warm active consumer cache
	-> initialize operation session cache
	-> start async pending-operation resume worker
	-> start expired-session sweeper
  -> start cache invalidation listeners
  -> mark service ready
```

If any mandatory cache cannot be loaded, the service should fail startup or remain not ready.

## Performance Guidelines

### What makes the request path fast

- API consumer authentication from memory
- BLZ lookup from memory
- product registration lookup from memory
- no per-request catalog parsing
- no per-request DB roundtrips for stable reference data
- no request worker blocked waiting for user 2FA confirmation

### What still dominates latency

- the live network call to the bank

Therefore the architecture should optimize local overhead aggressively, but must not compromise secret safety just to reduce a few milliseconds.

## Deployment Model

Recommended deployment units:

1. stateless gateway API instances
2. PostgreSQL as system of record

With one caveat:

- gateway instances are stateless with respect to PostgreSQL-backed business data, but they do hold sensitive in-memory pending operation sessions for decoupled authentication

### TLS termination

Recommended: terminate TLS at a reverse proxy or load balancer (e.g., nginx, Caddy, or a cloud load balancer).

The gateway application process receives plain HTTP on the internal network.

Required configuration when TLS is terminated externally:

- configure the middleware to trust `X-Forwarded-Proto` only from the load balancer
- reject or ignore `X-Forwarded-*` headers from untrusted upstream sources
- do not allow plain HTTP connections from external clients under any configuration

Not required in v1:

- Redis
- message broker
- workflow engine

Useful future additions if growth requires them:

- Redis for shared cache
- KMS or Vault for encryption key management
- asynchronous job worker for catalog refreshes and admin operations

## Packaging and Container Strategy

Packaging the admin CLI in the same container image as the API makes sense.

Recommended rule:

- one image
- two executables
- one shared service package

That means the image should contain:

- the `gateway` service executable for serving HTTP requests
- the `gateway_admin_cli` executable for operator workflows

This preserves operational simplicity while keeping the admin layer decoupled at the code and presentation boundaries.

Important distinction:

- same container image does not mean same presentation app
- same backend core does not mean presentation coupling

The API and CLI should remain separately deployable entrypoints even if they are shipped together.

## Technology Decisions

### HTTP framework: FastAPI

- all HTTP routing, request parsing, and response serialization use FastAPI
- Pydantic models are used for all request and response schemas
- FastAPI's `Depends` is used for dependency injection in routers

### CLI framework: Typer

- all admin CLI commands are implemented as Typer commands
- secret inputs use `typer.prompt(..., hide_input=True)`
- machine-readable output can be triggered with a `--json` flag
- destructive commands confirm with `typer.confirm(...)` unless `--yes` is passed

## Open Design Decisions and Recommended Answers

### Should the raw API key be stored in PostgreSQL?

No.

Recommended answer:

- store only `api_key_hash`
- present the generated API key only once during provisioning

This is stricter than the initial requirement and is the correct design.

### Should the product key be stored in PostgreSQL plaintext?

No.

Recommended answer:

- persist ciphertext only
- keep decryption key outside PostgreSQL

### Should transaction responses be cached?

Not in v1.

Recommended answer:

- keep the first version simple and non-retentive
- revisit only if measured latency and bank rate limits force the issue

### Should pending decoupled-authentication sessions be stored in PostgreSQL?

No.

Recommended answer:

- keep them only in an in-memory session cache in v1
- treat them as sensitive ephemeral execution state
- accept the routing limitation explicitly

### Should the API expose protocol now even though only FinTS is supported?

Yes.

Recommended answer:

- require a `protocol` field now
- support only `fints` initially
- select protocol-specific connectors behind a port

### Should the institute catalog keep every CSV column as first-class domain fields?

No.

Recommended answer:

- keep a small operational domain model
- store raw source payload separately for traceability

## Testing Strategy

### Domain tests

Test:

- aggregates
- value object validation
- selection policies

These tests must run with no framework and no database.

### Application tests

Test use cases with:

- fake repositories
- fake caches
- fake banking connector

### Infrastructure tests

Test:

- PostgreSQL repository mappings
- cache warmup behavior
- cache invalidation listeners
- anti-corruption adapter over Geldstrom
- secret-safe logging behavior

### Security regression tests

Add explicit tests that assert:

- secrets do not appear in logs
- secrets do not appear in serialized exceptions
- API keys are stored hashed
- product keys are stored encrypted

## Recommended First Implementation Scope

Phase 1 should implement only:

1. consumer access persistence and cache
2. institute catalog persistence and cache
3. encrypted product registration persistence and cache
4. health endpoints
5. list accounts endpoint
6. fetch transactions endpoint
7. get TAN methods endpoint
8. operation status endpoint for pending decoupled flows
9. secret-safe logging and error mapping
10. in-memory operation session cache and async resume worker

Do not add in phase 1:

- background transaction persistence
- bank response caching
- tenant-specific product registrations
- long-lived bank sessions across requests

Exception:

The app does need short-lived pending operation sessions across requests for decoupled 2FA. Those are runtime-only sessions, not durable long-lived customer sessions.

## Final Architectural Position

The gateway should be built as a **small orchestration app with a strong domain core for access control and reference data**, and a **strict anti-corruption boundary** to the existing Geldstrom library.

That yields the right tradeoff for this project:

- the business-critical persisted concepts are modeled cleanly
- request-time banking credentials remain transient
- PostgreSQL is removed from the normal hot path through startup-warmed caches
- the code stays readable because the business structure is visible in the folder layout
- the design remains portable because repositories, caches, and banking access are all behind ports

This is the architecture to implement under `apps/`, split across `gateway` and `gateway_admin_cli`.
