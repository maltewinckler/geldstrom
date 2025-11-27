# Read-Only FinTS Refactor PRD

## 1. Overview
We will realign `python-fints` around read-only banking capabilities (account discovery, balances, statements, holdings). The project currently mixes transfer/debit workflows, tangled protocol orchestration, and weak layering. This refactor pulls writing features out of scope, introduces a domain-oriented structure, and hardens reliability for data retrieval.

## 2. Goals
- Deliver clear domain abstractions for read-only FinTS operations (Account, Balance, TransactionFeed, Holdings, BankCapabilities).
- Separate domain, application, and infrastructure layers so protocol code is an adapter instead of the core.
- Provide resilient dialog/transport handling with timeouts, retries, and observable failures.
- Replace unsafe persistence/serialization (pickle blobs) with explicit `SessionState` DTOs.
- Improve deterministic parsing of inbound data; strict mode on by default with opt-in tolerant parsing.
- Establish testing strategy (unit, contract, property) to guard parsing, capability negotiation, and dialog lifecycle.

## 3. Non-Goals
- Sending SEPA transfers, debits, or TAN submissions for write operations.
- Maintaining backwards compatibility with existing APIs.
- Supporting legacy FinTS versions outside the read-only scope defined here.

## 4. User Stories & Test Hooks
1. **As a finance app integrator, I need to enumerate customer accounts with capabilities so I can show which features are available.**
   - *Acceptance/Test Notes*: Contract test that mocks bank BPD/UPD responses and verifies `AccountDiscoveryService` returns typed `BankCapabilities` and account DTOs; unit tests ensure unsupported segments raise `CapabilityMismatchError`.
2. **As a budgeting tool, I need to fetch balances reliably even when the bank intermittently fails so that dashboards stay accurate.**
   - *Tests*: Transport tests using a flaky HTTP stub verifying retry/backoff; application tests assert `BalanceService` surfaces `AccountSyncFailed` with rich telemetry after configured attempts.
3. **As an accountant, I need MT940/MT535 statements converted into structured entries with validation so ledger imports are correct.**
   - *Tests*: Property tests comparing parser↔serializer round-trips for statement payloads; fixture-based tests ensuring malformed segments trigger strict-mode errors and tolerant-mode warnings.
4. **As a compliance auditor, I need dialog/session snapshots that can be safely stored and resumed without executing arbitrary code.**
   - *Tests*: Serialization tests for `SessionState` to/from JSON/CBOR, ensuring sensitive fields are masked and `FinTSDialog` resumes only when signatures/IDs match.

## 5. Architecture & Approach
- **Domain Layer**: new package hosting entities, value objects, and domain services (no FinTS dependencies). Examples: `Account`, `Balance`, `Transaction`, `CapabilityMatrix`, `SessionState`.
- **Application Layer**: use-case services such as `AccountDiscoveryService`, `BalanceService`, `TransactionHistoryService`, `StatementDownloadService`, `HoldingsService`. They depend on domain interfaces (`BankSession`, `StatementGateway`).
- **Infrastructure Layer**: adapters implementing interfaces using FinTS protocol (parser/serializer, HTTP transport, TAN challenge reader). Transport exposes configurable timeouts, retry policy, and logging with masking.
- **Parser/Serializer Boundary**: strict parsing by default; tolerant mode opt-in with structured diagnostics. Segment coverage trimmed to read-only message families (e.g., HKSAL/HKKAZ/HKCAZ/HKEKA/HKWPD).
- **Dialog Lifecycle**: explicit state machine for authentication, keep-alive, and teardown. `FinTSDialog` limited to read flows; TAN responses handled only for view-only flows.
- **Persistence**: replace pickle-based `pause_dialog()` with `SessionState` dataclasses serialized to JSON/CBOR; ensure versioning and schema migration support.

## 6. Milestones
1. **Foundations (Weeks 1-2)**: define domain model, create packages, add typing/CI scaffolding, introduce `SessionState` serialization.
2. **Account Discovery (Weeks 3-4)**: implement `BankGateway` abstraction, migrate account listing, add contract tests, remove old transfer helpers.
3. **Balance & Transactions (Weeks 5-6)**: port balance and transaction history flows to new services, enforce strict parser mode, add retryable transport.
4. **Statements & Holdings (Weeks 7-8)**: support MT940/MT535 parsing into domain DTOs, add property-based tests, document tolerant parsing opt-in.
5. **Reliability & Cleanup (Weeks 9-10)**: finalize observability hooks, deprecate legacy APIs, complete documentation and migration notes.

## 7. Risks & Mitigations
- **Protocol coverage gaps**: maintain regression fixtures for representative banks; create ADR for unsupported segments.
- **State migrations**: ship a migration helper to convert legacy pickles to `SessionState` early.
- **Testing complexity**: invest in reusable fake FinTS server and scenario DSL to keep contract tests readable.

## 8. Success Metrics
- 90%+ unit test coverage in domain/application layers; parser property tests covering key segment families.
- Mean time to recover from transient HTTP failures < 5s in synthetic tests.
- Elimination of pickle usage and wildcard imports in new architecture.
- Documentation (README/PRD) referenced in onboarding and ADRs.
