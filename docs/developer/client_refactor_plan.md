# Legacy `fints/client.py` Refactor Plan

## 1. Goals
- Replace the monolithic legacy client (`fints/client.py`, ~1.5k LOC) with a maintainable, well-typed architecture.
- Align with the layered read-only stack already introduced (`fints/domain`, `fints/application`, `fints/infrastructure`).
- Preserve existing public APIs until we ship a migration guide (semantic versioning).
- Improve testability by isolating FinTS dialog handling, TAN workflows, and serialization.

## 2. Constraints & Assumptions
- Must keep compatibility with FinTS 3.0 PIN/TAN flows, including legacy edge cases (e.g., ING single-step auth).
- Existing `FinTS3PinTanClient` API is used widely; we need a shim for backwards compatibility.
- TAN approval can be synchronous (manual input) or decoupled (SecureGo). Both flows must stay supported.
- PyPI release cadence is slow; plan staged delivery behind feature flags where possible.

## 3. Target Architecture
1. **Domain abstractions**: Keep `FinTSOperations`, `NeedRetryResponse`, `TransactionResponse`, etc., but move them into purpose-specific modules under `fints/domain` (with dataclasses + enums).
2. **Infrastructure adapters**: Implement dialog/transport logic inside `fints/infrastructure/legacy_client` with smaller classes:
   - `DialogSessionManager` (system ID handling, login/logout context manager).
   - `ResponseProcessor` (maps `HIRMG/HIRMS` to structured results).
   - `OrderExecutor` per business capability (balance, transactions, transfers, etc.).
3. **Application services**: Build orchestration methods (e.g., `BalanceService`, `TransactionService`) that wrap the new infrastructure so read-only clients and future write-capable clients share code.
4. **Compatibility facade**: Expose a new `FinTSClient` class matching the old API surface but delegating to the new services. Emit deprecation warnings directing users to the newer layered APIs.

## 4. Migration Phases
### Phase A – Extraction & Analysis
- [ ] Inventory all public methods in `FinTS3PinTanClient` and categorize them (session mgmt, info retrieval, payment initiation).
- [ ] Document implicit state transitions (e.g., `_standing_dialog`, `_ensure_system_id`).
- [ ] Add high-level coverage around critical flows (balance fetch, transactions, SEPA transfer) to guard refactor.

### Phase B – Core Infrastructure Split
- [ ] Introduce `fints/infrastructure/legacy/dialog.py` housing `FinTSDialog` interactions (login, system ID, message exchange).
- [ ] Move TAN handling (`NeedTANResponse`, decoupled polling) into `fints/infrastructure/legacy/tan.py` with clean interfaces.
- [ ] Extract serialization/parsing helpers (`_log_response`, `_transaction_response`) into dedicated modules tested separately.

### Phase C – Service Layer & Facade
- [ ] Implement service objects for each operation cluster (accounts, balances, transactions, transfers) consuming the new infrastructure components.
- [ ] Create a `FinTSLegacyClient` facade exposing the same methods as `FinTS3PinTanClient` but internally delegating to services.
- [ ] Ship feature flag (env var or constructor flag) allowing users to opt into the new implementation for smoke testing.

### Phase D – Deprecation & Removal
- [ ] Announce deprecation timeline in docs and release notes.
- [ ] After at least one minor release, flip the default to the new client while keeping the old code path available for one more cycle.
- [ ] Eventually remove `fints/client.py`, keeping only the modern stack plus the thin compatibility shim.

## 5. Testing Strategy
- Expand unit coverage around the extracted components (dialog manager, TAN poller, response parser).
- Reuse existing integration tests (`tests/integration`) to validate end-to-end flows via the compatibility facade.
- Add load/regression tests for bank-specific quirks (ING one-step auth, decoupled TAN timeouts).

## 6. Tooling & Docs
- Update developer docs (`docs/developer/`) with module diagrams and extension guidance.
- Provide migration snippets showing how to instantiate the new services directly.
- Ensure lint/type-check config (mypy/ruff) covers new modules before switching defaults.

## 7. Open Questions
- Should payment initiation (transfers/debits) move into a separate opt-in package to reduce compliance risk?
- Do we keep `sepaxml` dependency, or wrap it behind an abstraction to allow alternative generators?
- How do we surface richer telemetry/logging without breaking existing log consumers?

This plan keeps implementation steps out-of-tree for now; once agreed, we can create issues/milestones per phase.
