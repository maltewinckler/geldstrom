# Vision

## Where we are going

> **A world where any developer can build financial software for Germany with the
> same ease as calling any other well-documented API — without needing to
> understand FinTS, navigate banking committee registrations, or implement TAN
> flows from scratch.**

## The future we are building toward

Today, building software that reads German bank data requires understanding a
protocol designed in 1995, obtaining a product registration from a banking
committee, hand-rolling TAN flows, and parsing a wire format that uses
apostrophes as segment terminators. Almost no tooling exists in the open-source
ecosystem.

We want to change that completely, across three horizons.

---

### Horizon 1 — Make the library the standard (now → 18 months)

The `geldstrom` Python library becomes the de-facto open-source FinTS client:
well-documented, actively maintained, and the first result when a German-market
developer searches for programmatic bank access. The gateway API makes it
accessible beyond Python.

**What success looks like:**
- The library is the obvious starting point for any Python developer working with
  German banks.
- The gateway ships a reliable, production-hardened single-node deployment that
  operators can run with confidence.
- The German fintech and indie developer community knows the project exists.

---

### Horizon 2 — Make integration trivial (18 months → 3 years)

Geldstrom grows into a complete integration platform for German financial data:

- **Webhook delivery** — Push-based transaction notification instead of polling.
- **Multi-user architecture** — One gateway deployment cleanly serves multiple
  end-users (e.g., an accounting SaaS serving its own customers).
- **Schema migrations (Alembic)** — Zero-downtime database upgrades; operators
  can upgrade the gateway without data loss.
- **Horizontal scalability** — Rate limiting and session state move to shared
  external stores (Redis), making multi-worker and multi-instance deployments
  trivially correct.

---

### Horizon 3 — Mature the ecosystem
*(3 years → beyond)*

- **Multi-language SDKs** — Typed client SDKs (TypeScript, Go) generated from
  the OpenAPI schema; an active community of contributors.
- **GDPR compliance toolkit** — Built-in consent management, data-subject
  request handling, and audit logging that hosted customers can rely on.

---

## What Geldstrom will never be

- **A black box** — All code is open and auditable.
- **A data broker** — We do not aggregate, store, or monetize users' financial
  data. Bank credentials and transaction data are never persisted beyond the
  minimum needed to complete a single request.
- **A payment service** — Geldstrom is read-only by design, permanently. There
  are no plans to add payment initiation.
- **A replacement for professional financial advice or regulated banking
  services** — Geldstrom is developer tooling, not a bank.
