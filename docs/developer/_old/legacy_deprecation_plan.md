# Legacy Client Deprecation Plan

## ✅ COMPLETED - November 29, 2025

The legacy client has been successfully removed! All functionality has been replaced
with the new domain-driven design architecture.

## Summary of Changes

### Files Removed
- `fints/client.py` (1058 LOC) - The monolithic legacy client
- `fints/dialog.py` - Old dialog module
- `fints/infrastructure/legacy/` (entire directory):
  - `dialog_manager.py`
  - `touchdown.py`
  - `pintan.py`
  - `tan.py`
  - `__init__.py`
- `fints/infrastructure/fints/services/` (entire directory - unused)
- `fints/infrastructure/fints/auth/workflow.py` - Only used by legacy client
- `fints/infrastructure/fints/auth/mechanisms.py` - Only used by legacy client
- `tests/unit/test_client.py` - Tests for legacy client

### Architecture Now
- All adapters use `FinTSConnectionHelper` directly (no fallback)
- All operations use `dialog/` and `operations/` modules
- TAN handling via `standalone_mechanisms.py`
- Clean separation: Domain → Application → Infrastructure

### Test Results
- 123 unit tests passing
- 15 integration tests passing
- Verified with Triodos and DKB banks

---

## Original Plan (Historical Reference)

## Goal

Fully remove `fints/client.py` (1000+ LOC monolith) and all `fints/infrastructure/legacy/` files by replacing their functionality with clean, modular infrastructure components.

## Historical State

### Files to Remove

| File | LOC | Current Usage |
|------|-----|---------------|
| `fints/client.py` | ~1058 | Used by all adapters, gateway, dialog |
| `fints/infrastructure/legacy/dialog_manager.py` | ~100 | Used by client.py |
| `fints/infrastructure/legacy/touchdown.py` | ~61 | Used by client.py |
| `fints/infrastructure/legacy/pintan.py` | ~26 | Re-export wrapper (can delete) |
| `fints/infrastructure/legacy/tan.py` | ~22 | Re-export wrapper (can delete) |

### Existing Infrastructure (from Phase 2/3) - NOT YET USED

**Important Discovery**: Phase 2 created clean infrastructure modules that are **orphaned** -
the adapters bypass them and still use `FinTS3PinTanClient` directly.

```
fints/infrastructure/fints/
├── dialog/                    # EXISTS - Created in Phase 2, NOT USED by adapters
│   ├── connection.py          # HTTPSDialogConnection ✓
│   ├── factory.py             # Dialog, DialogFactory, DialogState ✓
│   ├── responses.py           # ResponseProcessor ✓
│   └── transport.py           # MessageTransport ✓
│
├── protocol/                  # EXISTS - Created in Phase 2, NOT USED by adapters
│   └── parameters.py          # BankParameters, UserParameters ✓
│
├── auth/                      # EXISTS - Created in Phase 3, partially used
│   └── workflow.py            # PinTanWorkflow (used via legacy re-exports)
```

### Dependencies on `FinTS3PinTanClient`

```
fints/infrastructure/fints/adapters/
├── session.py      → _build_client(), uses client.get_information()
├── accounts.py     → _build_client(), uses client.get_information(), get_sepa_accounts()
├── balances.py     → _build_client(), uses client.get_balance()
├── transactions.py → _build_client(), uses client.get_transactions(), get_transactions_xml()
└── statements.py   → _build_client(), uses client.get_statements(), get_statement()

fints/infrastructure/gateway.py → FinTSReadOnlyGateway uses FinTS3PinTanClient
```

### What the Legacy Client Does

1. **Connection/Dialog Management** → Already in `dialog/` module (unused)
   - HTTP connection setup → `dialog/connection.py`
   - Dialog lifecycle → `dialog/factory.py`
   - System ID synchronization → needs extraction

2. **Bank Parameter Management** → Already in `protocol/` module (unused)
   - BPD/UPD management → `protocol/parameters.py`

3. **Authentication** → Already in `auth/` module
   - PIN/TAN workflow → `auth/workflow.py`
   - TAN mechanism selection → `auth/mechanisms.py`
   - Decoupled TAN polling → `auth/decoupled.py`

4. **Business Operations** → NEED TO CREATE
   - Balance queries (HKSAL)
   - Transaction history (HKKAZ/HKCAZ)
   - Statement retrieval (HKEKA)
   - SEPA transfers (HKCCS)
   - SEPA debits (HKDSE)

5. **State Serialization** → NEED TO EXTRACT
   - Session persistence (`deconstruct`/`set_data`)

---

## Migration Architecture

### Target Structure (Leveraging Existing Modules)

```
fints/infrastructure/fints/
├── dialog/                        # EXISTS: Low-level protocol (Phase 2)
│   ├── connection.py              # HTTPSDialogConnection ✓
│   ├── factory.py                 # Dialog, DialogFactory ✓
│   ├── responses.py               # ResponseProcessor ✓
│   └── transport.py               # MessageTransport ✓
│
├── protocol/                      # EXISTS: Parameters (Phase 2)
│   └── parameters.py              # BankParameters, UserParameters ✓
│
├── auth/                          # EXISTS: TAN workflow (Phase 3)
│   ├── challenge.py               # NeedTANResponse ✓
│   ├── decoupled.py               # DecoupledConfirmationPoller ✓
│   ├── mechanisms.py              # Encryption/Auth mechanisms ✓
│   └── workflow.py                # PinTanWorkflow ✓
│
├── operations/                    # NEW: Business operation implementations
│   ├── __init__.py
│   ├── accounts.py                # HKSPA, account info extraction
│   ├── balances.py                # HKSAL implementation
│   ├── transactions.py            # HKKAZ/HKCAZ with pagination
│   ├── statements.py              # HKEKA implementation
│   └── system_id.py               # System ID synchronization (from client)
│
├── adapters/                      # EXISTS: Domain port implementations
│   ├── session.py                 # UPDATE: Use dialog/ + operations/
│   ├── accounts.py                # UPDATE: Use operations/accounts
│   ├── balances.py                # UPDATE: Use operations/balances
│   ├── transactions.py            # UPDATE: Use operations/transactions
│   └── statements.py              # UPDATE: Use operations/statements
│
├── session.py                     # EXISTS: FinTSSessionState ✓
└── responses.py                   # EXISTS: Response types ✓
```

### Domain Layer Alignment

The plan aligns with your domain layer:

```
Domain (protocol-agnostic)          Infrastructure (FinTS-specific)
─────────────────────────          ────────────────────────────────
domain/model/accounts.py     ←──   operations/accounts.py (returns SEPAAccount)
  Account                          adapters/accounts.py (converts to Account)

domain/model/balances.py     ←──   operations/balances.py (returns MT940Balance)
  BalanceSnapshot                  adapters/balances.py (converts to BalanceSnapshot)

domain/model/transactions.py ←──   operations/transactions.py (returns raw data)
  TransactionFeed                  adapters/transactions.py (converts to TransactionFeed)

domain/ports/session.py      ←──   adapters/session.py (implements SessionPort)
  SessionPort                      Uses dialog/ for actual FinTS communication

domain/connection/session.py ←──   session.py (FinTSSessionState implements SessionToken)
  SessionToken protocol
```

**Key Principle**:
- `operations/` modules work with FinTS-specific types (SEPAAccount, MT940, segments)
- `adapters/` modules convert FinTS types to domain models
- Domain layer remains protocol-agnostic

---

## Migration Phases

### Phase A: Wire Up Existing Infrastructure (3-5 days) ✅ COMPLETED

**Goal**: Connect existing Phase 2 modules (dialog/, protocol/) which are currently orphaned

**Note**: Phase 2 already created `dialog/` and `protocol/` modules with full implementations,
but they're not being used. This phase wires them up.

#### A.1: Verify Existing Dialog Module ✅
- [x] Reviewed `fints/infrastructure/fints/dialog/factory.py` - Dialog class
- [x] Reviewed `fints/infrastructure/fints/dialog/connection.py` - HTTPSDialogConnection
- [x] Identified and fixed `_create_message_with_header` bug (missing `next_segment_number`)
- [x] Added `find_segment_first()` method to ProcessedResponse for segment access
- [x] Created `operations/system_id.py` for system ID synchronization

#### A.2: Verify Existing Protocol Module ✅
- [x] Reviewed `fints/infrastructure/fints/protocol/parameters.py`
- [x] BankParameters has all needed methods (find_segment, supports_operation, serialize)
- [x] UserParameters extracts account info correctly (get_accounts, get_account_capabilities)
- [x] Moved `FinTSOperations` enum into `operations/` package

#### A.3: Create Unit Tests ✅
- [x] Created `tests/unit/infrastructure/fints/test_dialog.py` (16 tests)
- [x] Created `tests/unit/infrastructure/fints/test_parameters.py` (18 tests)
- [x] All 34 new tests pass
- [x] Full unit test suite passes (120 tests)

**Files Created/Modified:**
- `tests/unit/infrastructure/__init__.py` - New
- `tests/unit/infrastructure/fints/__init__.py` - New
- `tests/unit/infrastructure/fints/test_dialog.py` - New (16 tests)
- `tests/unit/infrastructure/fints/test_parameters.py` - New (18 tests)
- `fints/infrastructure/fints/dialog/factory.py` - Fixed `_create_message_with_header`
- `fints/infrastructure/fints/dialog/transport.py` - Fixed `_create_customer_message`
- `fints/infrastructure/fints/dialog/responses.py` - Added `raw_response` and `find_segment_first`
- `fints/infrastructure/fints/operations/__init__.py` - New, exports FinTSOperations
- `fints/infrastructure/fints/operations/enums.py` - Moved from operations.py
- `fints/infrastructure/fints/operations/system_id.py` - New, SystemIdSynchronizer

### Phase B: Create Operation Modules (1-2 weeks) ✅ COMPLETED

**Goal**: Implement business operations using existing dialog/protocol modules

#### B.1: Create Operations Module Structure ✅
- [x] Created `fints/infrastructure/fints/operations/__init__.py`
- [x] Created `pagination.py` with `TouchdownPaginator` and `PaginatedResult`
- [x] Created `find_highest_supported_version()` helper

#### B.2: Account Operations ✅
- [x] Created `fints/infrastructure/fints/operations/accounts.py`
- [x] `AccountOperations.fetch_sepa_accounts()` - HKSPA/HISPA handling
- [x] `AccountOperations.get_accounts_from_upd()` - UPD extraction
- [x] `AccountOperations.merge_sepa_info()` - BIC enrichment
- [x] `AccountInfo` dataclass for raw account data

#### B.3: Balance Operations ✅
- [x] Created `fints/infrastructure/fints/operations/balances.py`
- [x] `BalanceOperations.fetch_balance()` - HKSAL5/6/7 support
- [x] `MT940Balance` and `BalanceResult` dataclasses
- [x] Automatic version selection via BPD

#### B.4: Transaction Operations ✅
- [x] Created `fints/infrastructure/fints/operations/transactions.py`
- [x] `TransactionOperations.fetch_mt940()` - HKKAZ5/6/7 with pagination
- [x] `TransactionOperations.fetch_camt()` - HKCAZ1 with pagination
- [x] `MT940TransactionResult` and `CAMTTransactionResult` dataclasses
- [x] CAMT message type extraction from BPD

#### B.5: Statement Operations ✅
- [x] Created `fints/infrastructure/fints/operations/statements.py`
- [x] `StatementOperations.list_statements()` - HKEKA listing
- [x] `StatementOperations.fetch_statement()` - Document retrieval
- [x] `StatementInfo` and `StatementDocument` dataclasses

#### B.6: System ID Operations ✅
- [x] Created `fints/infrastructure/fints/operations/system_id.py` (Phase A)
- [x] `SystemIdSynchronizer` for HKSYN3/HISYN4 exchange

**Files Created:**
- `fints/infrastructure/fints/operations/pagination.py` - Pagination support
- `fints/infrastructure/fints/operations/accounts.py` - HKSPA operations
- `fints/infrastructure/fints/operations/balances.py` - HKSAL operations
- `fints/infrastructure/fints/operations/transactions.py` - HKKAZ/HKCAZ operations
- `fints/infrastructure/fints/operations/statements.py` - HKEKA operations
- `tests/unit/infrastructure/fints/operations/__init__.py`
- `tests/unit/infrastructure/fints/operations/test_pagination.py` (8 tests)
- `tests/unit/infrastructure/fints/operations/test_accounts.py` (5 tests)
- `tests/unit/infrastructure/fints/operations/test_balances.py` (5 tests)

**Test Results:**
- 18 new operations tests
- 138 total unit tests passing

### Phase C: Refactor Adapters (1 week) ✅ COMPLETED

**Goal**: Update adapters to use operations modules instead of legacy client

**Strategy**: Feature flags allow gradual rollout - each adapter has a
`USE_NEW_INFRASTRUCTURE` flag that enables the new code path while keeping
legacy code for fallback. Once validated, legacy code will be removed.

#### C.1: Update Session Adapter ✅
- [x] Created `connection.py` with `FinTSConnectionHelper` and `ConnectionContext`
- [x] Added `_open_session_new()` using Dialog directly
- [x] Feature flag `USE_NEW_INFRASTRUCTURE` controls which path is used
- [x] Legacy code preserved for fallback

#### C.2: Update Account Adapter ✅
- [x] Added `_fetch_bank_capabilities_new()` using operations
- [x] Added `_fetch_accounts_new()` using `AccountOperations`
- [x] Added `_accounts_from_operations()` converter
- [x] Legacy code preserved for fallback

#### C.3: Update Balance Adapter ✅
- [x] Added `_fetch_balances_new()` using `BalanceOperations`
- [x] Added `_fetch_balance_new()` for single account
- [x] Added `_balance_from_operations()` converter
- [x] Legacy code preserved for fallback

#### C.4: Update Transaction Adapter ✅
- [x] Added `_fetch_history_new()` using `TransactionOperations`
- [x] Added `_locate_sepa_account_new()` helper
- [x] TAN polling logic preserved in legacy path
- [x] Feature flag controls code path

#### C.5: Update Statement Adapter ✅
- [x] Added `_list_statements_new()` using `StatementOperations`
- [x] Added `_fetch_statement_new()` for document retrieval
- [x] Added `_references_from_operations()` converter
- [x] Feature flag controls code path

**Files Created/Modified:**
- `fints/infrastructure/fints/adapters/connection.py` - NEW: Shared connection helper
- `fints/infrastructure/fints/adapters/session.py` - Updated with new path
- `fints/infrastructure/fints/adapters/accounts.py` - Updated with new path
- `fints/infrastructure/fints/adapters/balances.py` - Updated with new path
- `fints/infrastructure/fints/adapters/transactions.py` - Updated with new path
- `fints/infrastructure/fints/adapters/statements.py` - Updated with new path
- `fints/infrastructure/fints/adapters/__init__.py` - Updated exports

**Test Results:**
- 138 unit tests passing
- 5 integration tests passing (with legacy infrastructure enabled)

### Phase D: Update Gateway & Remove Legacy (1 week) ✅ PARTIAL

**Goal**: Complete the migration

#### D.1: Update Gateway ✅
- [x] Refactored `FinTSReadOnlyGateway` to delegate to adapters
- [x] Gateway is now a thin wrapper around adapters
- [x] ~500 lines of code removed from gateway.py

#### D.2: Migrate Unit Tests ✅
- [x] Updated `tests/unit/test_readonly_gateway.py` to test adapter methods
- [x] Added 16 adapter-specific tests
- [x] All 140 unit tests passing

#### D.3: Enable New Infrastructure 🔲 BLOCKED
- [ ] New infrastructure fails integration tests (parameter restoration issue)
- [ ] Issue: `ParameterStore.from_dict()` not properly restoring state
- [ ] Needs debugging before enabling USE_NEW_INFRASTRUCTURE = True
- [ ] Legacy files kept for backward compatibility:
  - `fints/client.py` - Still used by adapter legacy code paths
  - `fints/infrastructure/legacy/` - Re-exports for client.py

#### D.4: Final Testing ✅
- [x] Unit tests passing: 140 tests (124 core + 16 adapter)
- [x] Integration tests passing: 5 tests
- [x] Legacy infrastructure working correctly

**Note**: Full legacy removal blocked pending fix for new infrastructure parameter restoration.
The architecture is complete but the new code paths need debugging before the legacy
code can be removed.

---

## Backward Compatibility Strategy

### Keep Working
- `from fints import FinTS3Client` → New clean client
- `from fints import ReadOnlyFinTSClient` → Existing client
- All domain models unchanged

### Deprecate (with warnings)
- `from fints.client import FinTS3PinTanClient` → Use `FinTS3Client`
- `from fints.readonly import ReadOnlyFinTSClient` → Use `fints.ReadOnlyFinTSClient`

### Remove
- All direct usage of `FinTS3PinTanClient` internals
- `fints/infrastructure/legacy/*`

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking existing integrations | Phased rollout with deprecation warnings |
| Missing edge cases in new code | Comprehensive test coverage before removal |
| Performance regression | Benchmark critical paths |
| TAN workflow complexity | Auth module already extracted and tested |

---

## Testing Strategy

### Current Test Structure

| File | Purpose | Dependencies |
|------|---------|--------------|
| `tests/unit/test_client.py` | Tests `FinTS3PinTanClient` | Mock FinTS server fixture |
| `tests/unit/test_readonly_gateway.py` | Tests `FinTSReadOnlyGateway` helpers | `FinTS3Client` (legacy alias) |
| `tests/unit/test_domain_models.py` | Tests domain models | None (pure) |
| `tests/unit/conftest.py` | Mock FinTS server | ~200 LOC of HTTP handler |
| `tests/integration/test_integration.py` | Tests `ReadOnlyFinTSClient` | Real bank ✓ Already on new arch |

### Test Migration Plan

#### Phase A Testing: Infrastructure Verification

```
tests/unit/
└── infrastructure/
    └── fints/
        ├── test_dialog.py           # NEW: Test Dialog, DialogFactory
        ├── test_parameters.py       # NEW: Test BankParameters, UserParameters
        └── test_transport.py        # NEW: Test MessageTransport
```

- [ ] Create `tests/unit/infrastructure/fints/test_dialog.py`
  - Test dialog initialization with mock connection
  - Test message number sequencing
  - Test dialog state serialization
- [ ] Create `tests/unit/infrastructure/fints/test_parameters.py`
  - Test BPD segment parsing
  - Test UPD account extraction
  - Test version tracking

#### Phase B Testing: Operations Module Tests

```
tests/unit/
└── infrastructure/
    └── fints/
        └── operations/
            ├── test_accounts.py      # NEW: HKSPA handling
            ├── test_balances.py      # NEW: HKSAL handling
            ├── test_transactions.py  # NEW: HKKAZ/HKCAZ + pagination
            └── test_system_id.py     # NEW: HKSYN handling
```

- [ ] Create tests for each operation module
- [ ] Use mock Dialog to test segment construction
- [ ] Test pagination/touchdown handling
- [ ] Test TAN workflow integration points

#### Phase C Testing: Adapter Migration

**Strategy**: Migrate `test_client.py` tests to adapter tests

| Legacy Test | Migrate To | Notes |
|-------------|------------|-------|
| `test_get_sepa_accounts` | `test_accounts_adapter.py` | Test `FinTSAccountDiscovery` |
| `test_get_information` | `test_session_adapter.py` | Test `FinTSSessionAdapter` |
| `test_get_transactions` | `test_transactions_adapter.py` | Test `FinTSTransactionHistory` |
| `test_transfer_*` | `test_payment_operations.py` | Future: Payment operations |
| `test_tan_*` | `test_tan_workflow.py` | Test auth workflow |
| `test_resume` | `test_session_serialization.py` | Test session state persistence |
| `test_pin_wrong/locked` | `test_error_handling.py` | Test credential errors |

```
tests/unit/
└── infrastructure/
    └── fints/
        └── adapters/
            ├── test_session_adapter.py       # NEW
            ├── test_accounts_adapter.py      # NEW
            ├── test_balances_adapter.py      # NEW
            ├── test_transactions_adapter.py  # NEW
            └── test_error_handling.py        # NEW
```

#### Phase D Testing: Cleanup & Final Verification

- [ ] Delete `tests/unit/test_client.py` (after migration complete)
- [ ] Update `tests/unit/test_readonly_gateway.py` to not use `FinTS3Client`
- [ ] Run full test suite: `pytest tests/unit/`
- [ ] Run integration tests: `pytest tests/integration/ --run-integration`
- [ ] Verify no tests import from `fints.client`

### Mock Server Refactoring

The mock server in `tests/unit/conftest.py` (~200 LOC) simulates FinTS responses.

**Option 1: Keep mock server** (Recommended)
- The mock server tests real protocol behavior
- Useful for operations module tests
- Extract to `tests/fixtures/fints_mock_server.py`

**Option 2: Use response fixtures**
- Store captured FinTS responses as fixtures
- More lightweight, faster tests
- Less realistic but sufficient for unit tests

**Decision**: Keep mock server but refactor:
- [ ] Move mock server to `tests/fixtures/fints_mock_server.py`
- [ ] Make it importable by both legacy and new tests
- [ ] Update fixture to work with `Dialog` class directly (not just HTTP client)

### Test Coverage Requirements

Before removing `fints/client.py`:

| Area | Minimum Coverage | Status |
|------|------------------|--------|
| `dialog/` modules | 80% | TBD |
| `protocol/` modules | 80% | TBD |
| `operations/` modules | 90% | TBD |
| `adapters/` modules | 80% | TBD |
| `auth/` modules | 80% | Existing |
| Domain models | 90% | Existing ✓ |

### Testing Phases Summary

| Phase | New Tests | Migrate From | Delete |
|-------|-----------|--------------|--------|
| A | `test_dialog.py`, `test_parameters.py` | - | - |
| B | `test_operations/*.py` | - | - |
| C | `test_adapters/*.py` | `test_client.py` | - |
| D | - | - | `test_client.py` |

---

## Timeline Estimate

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase A: Wire Up Existing Infrastructure | 3-5 days | None |
| Phase B: Operation Modules | 1-2 weeks | Phase A |
| Phase C: Refactor Adapters | 1 week | Phase B |
| Phase D: Cleanup | 1 week | Phase C |

**Total**: 3-5 weeks

**Note**: Timeline is shorter than original estimate because Phase 2 already created
the dialog/protocol infrastructure - we just need to wire it up and add operations.

---

## Success Criteria

### Code Removal
- [ ] `fints/client.py` deleted (BLOCKED - see D.3)
- [ ] `fints/infrastructure/legacy/` directory deleted (BLOCKED - see D.3)
- [x] All adapters support both legacy and new infrastructure via feature flags
- [x] Clean import structure with no circular dependencies

### Testing
- [x] All unit tests pass (`pytest tests/unit/`) - 140 passing
- [x] All integration tests pass (`pytest tests/integration/ --run-integration`) - 5 passing
- [ ] `tests/unit/test_client.py` deleted (after migration)
- [ ] No tests import from `fints.client` directly
- [x] New test files cover:
  - [x] `tests/unit/infrastructure/fints/test_dialog.py` (16 tests)
  - [x] `tests/unit/infrastructure/fints/test_parameters.py` (18 tests)
  - [x] `tests/unit/infrastructure/fints/operations/test_*.py` (18 tests)
  - [ ] `tests/unit/infrastructure/fints/adapters/test_*.py` (future)

### Backward Compatibility
- [x] `from fints import FinTS3Client` works (new client)
- [x] `from fints import ReadOnlyFinTSClient` works
- [x] All domain models unchanged
- [x] No runtime deprecation warnings from internal code

### Current Status

**Completed:**
- Gateway refactored to delegate to adapters (500+ LOC removed)
- All adapters support dual-mode operation with feature flags
- Operations modules created (accounts, balances, transactions, statements)
- Comprehensive test coverage for new infrastructure
- All tests passing (140 unit, 5 integration)

**Status: FULLY RESOLVED ✅**

**Debugging Summary (comprehensive):**

### Issue 1: Dialog Init TAN (RESOLVED ✅)

1. **Root Cause Found:**
   - The legacy client sends **HKTAN** segment with `tan_process='4'` in the **main dialog init**
   - This HKTAN triggers the bank to return UPD (User Parameter Data)
   - Without HKTAN, the bank responds with error 9075 "SCA required"

2. **HKTAN Configuration for Dialog Init:**
   - `tan_process='4'` (dialog initialization)
   - `segment_type='HKIDN'` (the business segment type)
   - `tan_medium_name=None` ← **CRITICAL: NOT the actual TAN medium name!**
   - Use highest supported HKTAN version (7 in this case)

3. **Security Method Version Fix:**
   - HNVSK (encryption): `security_method_version=2` for two-step TAN
   - HNSHK (signature): `security_method_version=1`

### Issue 2: TAN with Business Operations (RESOLVED ✅)

**Finding (Nov 28, 2025):**

The legacy client sends HKTAN with **EVERY business operation**, not just during dialog init!

**Legacy Client Message Flow:**
```
Message 1: dialog=0, msg_num=1, segments=['HNSHK', 'HKIDN', 'HKVVB', 'HKSYN', 'HNSHA']
Message 2: dialog=xxx, msg_num=2, segments=['HNSHK', 'HKEND', 'HNSHA']
Message 3: dialog=0, msg_num=1, segments=['HNSHK', 'HKIDN', 'HKVVB', 'HKTAN', 'HNSHA']  ← Dialog init with HKTAN
Message 4: dialog=xxx, msg_num=2, segments=['HNSHK', 'HKSPA', 'HNSHA']  ← HKSPA doesn't need HKTAN
Message 5: dialog=xxx, msg_num=3, segments=['HNSHK', 'HKCAZ', 'HKTAN', 'HNSHA']  ← HKCAZ with HKTAN!
Message 6: dialog=xxx, msg_num=4, segments=['HNSHK', 'HKEND', 'HNSHA']
```

**Solution Implemented: Dialog-level HKTAN Injection**

Modified `Dialog.send()` to automatically inject HKTAN after business segments:

1. **Dialog class changes (`fints/infrastructure/fints/dialog/factory.py`):**
   - Added `security_function` parameter to Dialog.__init__()
   - Added `is_two_step_tan` property
   - Added `_inject_hktan_for_business_segments()` method
   - Added `_build_hktan_for_segment()` method
   - Modified `send()` to call injection for two-step TAN dialogs
   - Created `DIALOG_SEGMENTS` set for segments that don't need HKTAN

2. **Excluded Segments (no HKTAN needed):**
   - `HKIDN`, `HKVVB`, `HKEND`, `HKSYN` (dialog management)
   - `HKTAN` (to prevent recursion)
   - `HKSPA` (account list - based on legacy client behavior)
   - `HKSAL` (balance query - based on legacy client behavior)

3. **HKTAN Configuration:**
   - `tan_process='4'`
   - `segment_type=<business_segment_type>` (e.g., 'HKCAZ', 'HKSAL')
   - `tan_medium_name=None` (must NOT be set)
   - Version determined from HITANS in BPD

### Files Modified:
- `fints/infrastructure/fints/dialog/factory.py` - Added HKTAN injection in Dialog.send()
- `fints/infrastructure/fints/adapters/connection.py` - Added HKTAN to main dialog init, fixed HNVSK version, pass security_function to Dialog
- `fints/infrastructure/fints/operations/balances.py` - Fixed null handling in balance parsing
- `fints/infrastructure/fints/auth/standalone_mechanisms.py` - Created new file
- `fints/infrastructure/fints/auth/__init__.py` - Added exports

### Test Results with USE_NEW_INFRASTRUCTURE = True:
- 124 unit tests ✅
- 16 integration tests ✅
  - test_connect_and_list_accounts ✅
  - test_fetch_balance ✅
  - test_fetch_transactions ✅
  - test_session_reuse ✅
  - test_fetch_capabilities ✅
  - test_multiple_operations_same_session ✅
  - test_all_accounts_balance ✅
  - test_session_state_contains_parameters ✅
  - test_session_reuse_skips_sync_dialog ✅
  - test_session_state_serialization_roundtrip ✅
  - test_transactions_with_date_range ✅
  - test_transactions_empty_range ✅
  - test_invalid_account_raises_error ✅
  - test_auto_connect_on_operation ✅
  - test_new_infrastructure_flag_enabled ✅
  - test_dialog_hktan_injection ✅

**All operations now work with the new infrastructure!**

---

## DKB Bank Integration (November 28, 2025)

During integration testing with DKB, we discovered several bank-specific behaviors:

### 1. Decoupled TAN for Dialog Init
DKB requires decoupled TAN (app approval) for the main dialog initialization. After sending HKTAN with dialog init, the bank returns code `3955` and we must poll with `HKTAN(tan_process='S')` until the user approves in their DKB-App.

### 2. One-Step Auth for Sync Dialog
Even when using two-step TAN (method 940) for the main dialog, the sync dialog (to obtain system ID) must use one-step auth (`security_function=999`). Using two-step auth for sync causes immediate rejection.

### 3. Smart HKTAN Injection Based on HIPINS
DKB requires HKTAN injection for HKSPA and HKSAL, unlike Triodos which doesn't. Instead of blindly injecting HKTAN for all business segments, we now check the bank's HIPINS (in BPD) to see which operations actually require TAN:
```python
def _segment_requires_tan(self, segment_type: str) -> bool:
    hipins = self._parameters.bpd.segments.find_segment_first(HIPINS1)
    if hipins and hasattr(hipins.parameter, "transaction_tans_required"):
        for req in hipins.parameter.transaction_tans_required:
            if req.transaction == segment_type:
                return req.tan_required
    return True  # Assume required if not specified
```

This prevents unnecessary 2FA requests for banks that don't require TAN for certain operations.

### 4. Accounts in UPD Only
Some banks (like DKB) don't return accounts in HISPA response - they only provide account info in UPD (HIUPD). Added fallback to check UPD if HISPA returns nothing.

### 5. Nullable account_information in HIUPD
DKB's HIUPD6 has `account_information=None`, so we made the UPD parsing more robust with getattr() fallbacks.

These findings highlight the importance of testing with multiple banks, as FinTS implementations vary significantly between institutions.

