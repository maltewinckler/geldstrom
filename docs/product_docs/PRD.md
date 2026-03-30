# Product Requirements Document — Geldstrom Banking Gateway

**Status:** Draft
**Last updated:** 2026-03-27
**Owner:** Malte Winckler

---

## 1. Overview

Geldstrom consists of two independently useful but tightly related products:

| Component | What it is | Who uses it |
|---|---|---|
| `geldstrom` *(library)* | Open-source Python library for FinTS 3.0 | Python developers directly |
| **Banking Gateway** *(this PRD)* | Managed REST API hosted by Geldstrom; optionally self-hostable with own FinTS product key | Application developers in any language |
| `gw-admin` *(CLI)* | Operator tooling bundled with the gateway | Infrastructure operators |

This PRD covers the **Banking Gateway** and its operator CLI. The `geldstrom`
library has its own release cadence and is versioned separately.

The primary deployment model is a **managed hosted service** operated by Malte
Winckler. The FinTS product registration requirement (approval by the *Deutsche
Kreditwirtschaft*) is a significant entry barrier for individual operators; the
hosted service absorbs this barrier. Operators who obtain their own product
registration may self-host for personal use; commercial operation by third
parties is not permitted.

---

## 2. Problem statement

German financial institutions expose bank account data exclusively through
**FinTS 3.0**, a stateful, binary-adjacent protocol from 1999 that:

- Requires a product registration with the *Deutsche Kreditwirtschaft* (a
  committee of German banking associations).
- Uses a bespoke wire format with segment-level versioning and encryption.
- Requires **decoupled TAN (2FA)** for most read operations — meaning requests
  can take tens of seconds to complete while the user approves on their phone.
- Has virtually no modern open-source tooling.

As a result, even simple tasks like reading a bank balance require a significant
engineering investment. Developers are forced to either license expensive
proprietary middleware (FinAPI, figo) or implement the protocol from scratch.

**Geldstrom's gateway eliminates this entirely.** An operator deploys one
instance, loads the institute catalog, and any authenticated API client can
fetch accounts, balances, and transactions with standard HTTP calls.

---

## 3. Goals

### 3.1 MVP goals (this release)

| # | Goal | Success metric |
|---|---|---|
| G1 | Developers can fetch balances and transactions from any supported German bank. | End-to-end request completes successfully for ≥ 3 major banks. |
| G2 | 2FA / decoupled TAN works without developer intervention. | Client polls `/operations/{id}` and receives result after TAN approval. |
| G3 | Operators can deploy the gateway to a single server in under 30 minutes. | Getting-started guide reproducible in a clean environment. |
| G4 | API keys are managed securely. | Keys stored as Argon2id hashes; raw key shown exactly once. |
| G5 | The institute catalog covers all publicly listed German FinTS banks. | `gw-admin catalog sync` loads the Bundesbank CSV without errors. |

### 3.2 Non-goals for MVP

- Payment initiation (SEPA transfers, direct debits). **Permanently off the
  roadmap, not just deferred.**
- Multi-tenant user isolation (end-users' own bank credentials scoped per consumer).
- Horizontal scaling / multi-worker deployment.
- Schema migrations (the initial schema is stable enough for MVP).

---

## 4. Target users

### 4.1 Primary: The SWEN User/Admin

A developer using SWEN which is a personal finance app that relies on automatic data imports.
This API should easily be integrated into the SWEN ecosystem. They want to deply the swen app on
their homelabs and do not want to understand FinTS and the bureaucracy around it.

**Characteristics:**
- Building a product that accesses *their users'* German bank accounts — a
  personal finance app, accounting integration, bookkeeping tool, or tax
  preparation service.
- May use any language/framework (the gateway exposes a REST API).
- Expects bank credentials and transaction data to be handled securely and
  never persisted.

### 4.2 Secondary: The Python developer

Someone building a script, automation, or data pipeline directly in Python. They
use the `geldstrom` library directly and may never interact with the gateway.

### 4.3 Operator

The person (often the same as the developer) who deploys and administers the
gateway. Has access to `gw-admin` and the database.

---

## 5. Features

### 5.1 Current capabilities (implemented)

#### Banking operations

| Operation | Endpoint | Notes |
|---|---|---|
| List accounts | `POST /v1/banking/accounts` | Returns all SEPA accounts |
| Get balances | `POST /v1/banking/balances` | Returns booked + available |
| Fetch transactions | `POST /v1/banking/transactions` | Max 365-day range |
| List TAN methods | `POST /v1/banking/tan-methods` | Enumerates bank's 2FA options |
| Poll operation status | `GET /v1/banking/operations/{id}` | Decoupled TAN completion |

All banking endpoints accept `blz` (BLZ), `user_id`, `password`, and optional
`tan_method` / `tan_medium`. Responses are either:
- **200 Completed** — data returned immediately (no TAN required).
- **202 Pending** — a decoupled TAN challenge is in progress; client polls the
  operations endpoint until completion.

#### Security

- API key authentication (Bearer token), hashed with Argon2id.
- Per-consumer request rate limiting (60 req/min default, configurable).
- `Cache-Control: no-store` on all responses.
- `X-Request-ID` correlation header (UUID-validated).
- Structured JSON logging with secret field redaction.

#### Admin CLI (`gw-admin`)

| Command group | Commands |
|---|---|
| `users` | `create`, `list`, `update`, `disable`, `reactivate`, `delete`, `rotate-key` |
| `catalog` | `sync` (loads Bundesbank FinTS CSV) |
| `product` | `update` (sets FinTS product key + version) |
| `db` | `init` (create DB + schema), `reset` (truncate all tables) |
| `inspect` | `state` (operator health snapshot) |

---

### 5.2 Planned features (post-MVP)

#### Near-term (Horizon 1 — next 6 months)

| Feature | Motivation |
|---|---|
| **Alembic migrations** | Enable schema changes without data loss; required for any post-MVP feature. Currently `db init` is idempotent but cannot evolve an existing schema. |
| **Redis-backed rate limiting** | Make the rate limiter correct for multi-worker uvicorn deployments. Current in-process implementation explicitly warns on startup when `GATEWAY_WORKERS > 1`. |
| **Redis-backed session store** | The pending-operation session store is currently in-process memory; a Redis backend would make multi-worker and multi-instance deployments safe. |
| **OpenAPI SDK generation** | Generate typed client SDKs (TypeScript, Go) from the FastAPI schema. |
| **Webhook delivery** | Push-notify a configured endpoint when a pending operation completes, eliminating client-side polling. |

#### Medium-term (Horizon 2 — 6–18 months)

| Feature | Motivation |
|---|---|
| **Multi-user scoping** | Allow consumer A to only see operations initiated by consumer A. Currently all consumers share one namespace for operations. |
| **Pagination on `list_users`** | Currently unbounded; becomes a problem at scale. |
| **Structured audit log** | Per-operation audit trail persisted to the database. Important for compliance and GDPR data-access requests. |

#### Long-term (Horizon 3 — 18 months+)

| Feature | Motivation |
|---|---|
| **Multi-language SDKs** | Typed client SDKs (TypeScript, Go) generated from the OpenAPI schema. |
| **GDPR consent management** | Built-in consent tracking and data-subject request handling for products serving end-users. |

---

## 6. Architecture

### 6.1 Current architecture

```
┌───────────────────────────────────────────────────────────┐
│               Banking Gateway (FastAPI / uvicorn)          │
│                                                            │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │ Auth     │  │ Rate Limiter │  │ Request ID / Cache │  │
│  │ (Argon2) │  │ (in-process) │  │ Control middleware │  │
│  └──────────┘  └──────────────┘  └────────────────────┘  │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │           Application (Use Cases)                    │ │
│  │  ListAccounts  GetBalances  FetchTransactions        │ │
│  │  GetTanMethods  GetOperationStatus                   │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
│  ┌──────────────────┐  ┌──────────────────────────────┐   │
│  │ In-Memory Caches │  │ Geldstrom FinTS Connector    │   │
│  │ - Consumers      │  │ (asyncio.to_thread adapter)  │   │
│  │ - Institutes     │  └──────────────────────────────┘   │
│  │ - Op. Sessions   │                  │                   │
│  └──────────────────┘                  ▼                   │
│                              ┌─────────────────┐           │
│  ┌──────────────────┐        │  German Bank    │           │
│  │   PostgreSQL     │        │  (FinTS/HTTPS)  │           │
│  │  (source of      │        └─────────────────┘           │
│  │   truth)         │                                       │
│  └──────────────────┘                                       │
└───────────────────────────────────────────────────────────┘
```

**Key design constraints in the current build:**

- The `geldstrom` library is synchronous (blocking). All bank calls run in a
  thread pool via `asyncio.to_thread`.
- Caches (consumers, institutes, operation sessions) are in-process. A
  PostgreSQL `LISTEN/NOTIFY` listener invalidates the consumer and institute
  caches when `gw-admin` makes changes.
- The background **resume worker** polls pending decoupled-TAN sessions every
  5 seconds, advancing them to `COMPLETED`, `FAILED`, or `EXPIRED`.

### 6.2 MVP deployment (single-node)

```
                  ┌─────────────────────────────────┐
  Internet        │           Single Server          │
  ─────────────▶  │                                  │
                  │  ┌─────────────┐                 │
                  │  │  Caddy /    │                 │
                  │  │  Nginx      │  TLS termination │
                  │  │  (reverse   │  + rate limiting │
                  │  │   proxy)    │  + access log    │
                  │  └──────┬──────┘                 │
                  │         │                        │
                  │  ┌──────▼──────┐                 │
                  │  │  uvicorn    │  1 worker        │
                  │  │  (gateway)  │                  │
                  │  └──────┬──────┘                 │
                  │         │                        │
                  │  ┌──────▼──────┐                 │
                  │  │ PostgreSQL  │                  │
                  │  └─────────────┘                 │
                  └─────────────────────────────────┘
```

**MVP deployment constraints:**
- Single uvicorn worker (`GATEWAY_WORKERS=1`) — avoids the multi-process
  correctness issues with in-process caches and rate limiter.
- Rate limiting delegated to the reverse proxy (Caddy `caddy-ratelimit` or
  Nginx `limit_req`), removing the need for Redis at MVP.
- TLS terminated at the reverse proxy.
- `gw-admin` runs locally on the same server against the same PostgreSQL
  instance.

### 6.3 Scalability path (post-MVP)

The architecture is designed to scale horizontally with the following additions,
each of which can be introduced independently:

```
Step 1: Multi-worker (same server)
  → Add Redis for rate limiting (slowapi or custom)
  → Add Redis for operation session store
  → GATEWAY_WORKERS can be set to CPU count

Step 2: Multi-instance (multiple servers)
  → Redis already shared; rate limits and sessions are globally consistent
  → PostgreSQL NOTIFY still works for cache invalidation across instances
  → Resume worker needs a distributed lock (Redis SETNX pattern) to avoid
    duplicate processing

Step 3: Infrastructure separation
  → PostgreSQL → managed RDS / Cloud SQL (connection pooling via PgBouncer)
  → Redis → managed ElastiCache / Redis Cloud
  → Gateway → multiple instances behind a load balancer
  → gw-admin CI/CD deploys Alembic migrations before rolling the service
```

No application-layer changes are required for Steps 1–2 beyond swapping store
implementations behind the existing port interfaces.

---

## 7. Decisions record

All founding questions have been answered. No open questions remain.

| # | Question | Decision |
|---|---|---|
| OQ-1 | Self-hosted only, or hosted/managed? | **Hosted managed service is the primary product.** The FinTS product registration barrier motivates a managed offering. Self-hosting with own product key remains supported for personal use. |
| OQ-2 | Developer's own account, or end-users' accounts? | **Serving end-users.** The gateway is consumed by applications that access their users' bank accounts on their behalf. |
| OQ-3 | SEPA payment initiation on the roadmap? | **No — permanently off the roadmap.** Geldstrom is read-only by design. |
| OQ-4 | DACH-only or EU Open Banking? | **FinTS / DACH-only.** PSD2/XS2A is not on the current roadmap. |
| OQ-5 | Commercial licensing model? | **Commercial exclusivity to Malte Winckler.** The `geldstrom` library remains LGPL-3.0. The managed gateway service may only be operated commercially by Malte Winckler. Source is available for personal/evaluation self-hosting. |
| OQ-6 | Target MVP launch date? | **No fixed date.** Shipping when production-hardened, not to a deadline. |
| OQ-7 | GDPR / data persistence requirements? | **Minimize data persistence.** Bank credentials and transaction data must not be persisted beyond what is strictly necessary to complete a single request. |

---

## 8. Out of scope (explicitly)

- Payment initiation of any kind (SEPA credit transfer, direct debit) — permanently
- PSD2 / EU Open Banking / XS2A support
- Mobile SDKs
- UI / dashboard
- Non-German banks
- Persistent storage of bank credentials or transaction data

---

## 9. Technical dependencies & constraints

| Item | Current | Notes |
|---|---|---|
| Python | 3.13+ | Minimum version; uses `StrEnum`, `tomllib`, modern typing |
| Database | PostgreSQL 14+ | asyncpg driver; SQLAlchemy 2.0 ORM |
| FinTS product registration | Required | Issued by Deutsche Kreditwirtschaft; free, ~2 week turnaround |
| Bank TAN method | Decoupled only | SMS-TAN and chip-TAN not supported; most modern German banks support decoupled |

---

## 10. Data management & GDPR

Because the gateway serves end-users' bank accounts on behalf of third-party
applications, minimizing data persistence is both a product principle and a GDPR
requirement.

**Current state (implemented):**
- Bank credentials (`user_id`, `password`) are accepted per-request and never
  written to the database or any persistent store.
- Transaction data is returned in the HTTP response and never stored.
- During a pending decoupled-TAN flow, only operation *metadata* is held
  in-memory (operation ID, status, timestamps, bank reference). The operation
  session has a 120-second TTL and is discarded on completion or expiry.
- All responses carry `Cache-Control: no-store`.
- Structured logs redact known secret fields before writing.

**Requirements going forward:**
- Any new feature must be reviewed for data minimization before merging.
- No new persistent table may store raw bank credentials, account numbers beyond
  what is needed for routing, or transaction content.
- When the structured audit log is implemented (Horizon 2), it must log
  *operation events* (initiated, completed, failed) without recording credential
  values or full transaction payloads.
- GDPR data-subject deletion requests can be served by deleting the consumer
  record; no other table should hold personally identifiable information beyond
  what is already scoped to that consumer.

---

## 11. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Bank changes FinTS endpoint or segment version | Medium | High | Segment versioning system in the library; tests against known-good messages |
| Product registration revoked or expires | Low | Critical | Product key is stored in the database and configurable via `gw-admin product update` without a restart |
| In-process state lost on restart | High (by design) | Low | Operation sessions are short-lived (2 min TTL); clients handle 404 and retry |
| Rate limiter bypassed in multi-worker deployment | High if workers > 1 | Medium | Startup warning; MVP docs explicitly require GATEWAY_WORKERS=1 until Redis is added |
| Bank credentials transiently in-process during TAN resume | Low | Low | Read-only only; payment initiation is permanently off the roadmap |
