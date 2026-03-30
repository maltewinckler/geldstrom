# Mission

> **Geldstrom makes German bank data programmable.**

We give developers secure, reliable, standards-based access to their users'
German bank accounts — without requiring them to understand FinTS, negotiate
product registrations, or deal with the decades-old German online-banking
protocol stack themselves.

## In one sentence

Geldstrom's mission is to eliminate the accidental complexity between a developer
and a German bank account, so that building financial software in Germany is as
straightforward as calling any other well-documented API.

## What this means in practice

| For whom | What we do |
|---|---|
| **Python developers** | A carefully designed open-source library (`geldstrom`) that speaks FinTS 3.0 natively, with modern type-safe Python idioms and full TAN/2FA support. |
| **Application builders** | A managed REST gateway (hosted by Geldstrom) that wraps the library behind a clean JSON API with API-key auth, session management, and operation-status polling — so any language or framework can consume it. Operators who obtain their own FinTS product registration may also self-host. |
| **Infrastructure operators** | An admin CLI (`gw-admin`) for day-to-day management: users, institute catalog, product registration, database setup. |

## What we do not do

- **No payment initiation** — Geldstrom is read-only by design. Moving money is
  out of scope for the current product. *(See PRD for future considerations.)*
- **No third-party commercial deployment** — The managed gateway service is
  operated exclusively by Malte Winckler. The FinTS product registration
  requirement (issued by the *Deutsche Kreditwirtschaft*) creates a significant
  entry barrier; the hosted service absorbs it on behalf of developers. Third
  parties may self-host for personal use with their own product registration;
  commercial operation by third parties is not permitted.

- **No payment initiation, ever** — Geldstrom is permanently read-only. SEPA
  transfers, direct debits, and any form of write operation are out of scope.

- **FinTS / DACH-market only** — FinTS 3.0 is a German-only protocol. PSD2/EU
  Open Banking is not on the current roadmap.
