# Legacy Code Cleanup Plan

**Status:** Planning
**Last Updated:** 2024-12-01

## Overview

This document tracks the removal of legacy Container-based code from geldstrom, completing the migration to Pydantic-based models.

## Current Architecture

```
geldstrom/
├── infrastructure/fints/protocol/  # ✅ NEW - Pydantic-based (KEEP)
│   ├── base.py                     # FinTSModel, FinTSSegment, SegmentSequence
│   ├── parser.py                   # FinTSParser, FinTSSerializer
│   ├── formals/                    # Pydantic DEGs
│   └── segments/                   # Pydantic segments
│
├── types.py        # ⚠️ LEGACY - Container, Field, SegmentSequence bridge
├── fields.py       # ⚠️ LEGACY - DataElementField, ContainerField
├── formals.py      # ⚠️ LEGACY - DataElementGroup definitions
├── parser.py       # ⚠️ LEGACY - FinTS3Parser, FinTS3Serializer
├── segments/       # ⚠️ LEGACY - Container-based segments (12 files)
└── models.py       # ⚠️ LEGACY - Container-based models
```

## Blocking Issues

### Issue 1: SegmentSequence Bridge
The legacy `SegmentSequence` in `types.py` provides critical functionality missing from the Pydantic version:

| Feature | Legacy (types.py) | Pydantic (protocol/base.py) |
|---------|-------------------|----------------------------|
| `__init__(bytes)` | ✅ Parses bytes | ❌ Missing |
| `render_bytes()` | ✅ Serializes | ❌ Missing |
| `find_segments()` | ✅ | ✅ |
| `find_segment_first()` | ✅ | ✅ |
| `print_nested()` | ✅ | ❌ Missing |

**Used by:**
- `infrastructure/fints/protocol/parameters.py` - BPD/UPD serialization
- `infrastructure/fints/dialog/connection.py` - Message handling
- `infrastructure/fints/auth/challenge.py` - TAN handling
- 6 other infrastructure files

### Issue 2: Legacy Parser Still Used
`infrastructure/fints/protocol/parameters.py` imports `FinTS3Serializer` from the legacy parser.

### Issue 3: Test Dependencies
10 test files with 27 imports from legacy modules:
- `tests/unit/test_types.py`
- `tests/unit/test_formals.py`
- `tests/unit/test_models.py`
- `tests/unit/test_message_parser.py`
- `tests/unit/test_message_serializer.py`
- `tests/unit/conftest.py`
- And 4 more...

---

## Recommended Approach: Tests First

### Why Tests First?

1. **Safety Net:** Updated tests catch regressions during cleanup
2. **Documentation:** Tests document expected behavior
3. **Confidence:** Passing tests prove the new code works
4. **Incremental:** Can validate each step of migration

### Phase 0: Test & Example Stabilization (DO FIRST)

#### 0.1 Fix Existing Test Failures
- [ ] Fix `test_implode_roundtrip_simple` serializer test
- [ ] Ensure all 506 unit tests pass

#### 0.2 Add Pydantic-Focused Tests
- [ ] Add tests for Pydantic `SegmentSequence` in `tests/unit/protocol/test_base.py`
- [ ] Add tests for `FinTSParser` round-trip (parse → serialize → parse)
- [ ] Add tests for `FinTSSerializer` with various segment types

#### 0.3 Update Examples
- [ ] Verify `examples/fetch_balance.py` works end-to-end
- [ ] Verify `examples/fetch_transactions.py` works end-to-end
- [ ] Verify `examples/test_tan_flow.py` works with TAN approval
- [ ] Add `examples/list_accounts.py` - simplest possible example

#### 0.4 Add Integration Test Coverage
- [ ] Test that connects, fetches BPD/UPD, disconnects
- [ ] Test that lists accounts without TAN
- [ ] Test that fetches balance (may need TAN)
- [ ] Document which tests require TAN approval

---

## Phase 1: Extend Pydantic SegmentSequence

### 1.1 Add Missing Methods to `protocol/base.py`
- [ ] Add `render_bytes()` method using `FinTSSerializer`
- [ ] Add class method `from_bytes(data: bytes)` using `FinTSParser`
- [ ] Add `print_nested()` for debugging (optional)

### 1.2 Update Infrastructure Imports
- [ ] `infrastructure/fints/protocol/parameters.py` - use Pydantic SegmentSequence
- [ ] `infrastructure/fints/dialog/connection.py`
- [ ] `infrastructure/fints/dialog/responses.py`
- [ ] `infrastructure/fints/auth/challenge.py`
- [ ] `infrastructure/fints/auth/standalone_mechanisms.py`
- [ ] `infrastructure/fints/protocol/segments/message.py`

### 1.3 Validate
- [ ] Run full test suite
- [ ] Run examples manually
- [ ] Run integration tests with `--run-integration`

---

## Phase 2: Remove Legacy Modules

### 2.1 Remove Legacy Types
- [ ] Delete `geldstrom/types.py` (or keep minimal re-exports)
- [ ] Update any remaining imports

### 2.2 Remove Legacy Fields
- [ ] Delete `geldstrom/fields.py`
- [ ] Update any remaining imports

### 2.3 Remove Legacy Formals
- [ ] Delete `geldstrom/formals.py`
- [ ] Update any remaining imports

### 2.4 Remove Legacy Parser
- [ ] Delete `geldstrom/parser.py`
- [ ] Update any remaining imports

### 2.5 Remove Legacy Segments
- [ ] Delete `geldstrom/segments/` directory (12 files)
- [ ] Update any remaining imports

### 2.6 Remove Legacy Models
- [ ] Check `geldstrom/models.py` usage
- [ ] Delete if unused, or migrate if needed

---

## Phase 3: Test Cleanup

### 3.1 Remove/Update Legacy Tests
- [ ] `tests/unit/test_types.py` - Remove or update for Pydantic
- [ ] `tests/unit/test_formals.py` - Remove legacy, keep Pydantic tests
- [ ] `tests/unit/test_models.py` - Remove or migrate
- [ ] `tests/unit/test_message_parser.py` - Update for new parser
- [ ] `tests/unit/test_message_serializer.py` - Update for new serializer
- [ ] `tests/unit/conftest.py` - Remove legacy fixtures

### 3.2 Final Validation
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All examples work
- [ ] No imports from deleted modules

---

## Phase 4: Documentation & Cleanup

### 4.1 Update Documentation
- [ ] Update README.md with new import paths
- [ ] Remove/archive old developer docs in `docs/developer/_old/`
- [ ] Update any docstrings referencing legacy code

### 4.2 Update Package Exports
- [ ] Clean up `geldstrom/__init__.py`
- [ ] Ensure public API is well-defined
- [ ] Add `__all__` exports

### 4.3 Final Cleanup
- [ ] Remove `USE_PYDANTIC_PARSER` flag (always True)
- [ ] Remove `STRICT_PARSING` if not needed
- [ ] Remove deprecation warnings
- [ ] Bump version number

---

## Files to Delete (Final List)

```
geldstrom/types.py          # 582 lines - Container, Field, legacy SegmentSequence
geldstrom/fields.py         # 337 lines - DataElementField, etc.
geldstrom/formals.py        # 1100+ lines - Legacy DEGs
geldstrom/parser.py         # 475 lines - FinTS3Parser/Serializer
geldstrom/models.py         # TBD - Check usage first
geldstrom/segments/         # 12 files - Legacy segments
  ├── __init__.py
  ├── accounts.py
  ├── auth.py
  ├── bank.py
  ├── base.py
  ├── debit.py
  ├── depot.py
  ├── dialog.py
  ├── journal.py
  ├── message.py
  ├── saldo.py
  ├── statement.py
  └── transfer.py
```

**Estimated lines to remove:** ~3,500+

---

## Progress Tracking

| Phase | Status | Completed | Notes |
|-------|--------|-----------|-------|
| 0.1 Fix tests | ✅ Done | 2024-12-01 | Fixed SegmentSequenceField to use legacy parser |
| 0.2 Add Pydantic tests | ✅ Done | 2024-12-01 | Fixed test class names, added serialization round-trip tests |
| 0.3 Update examples | ✅ Done | 2024-12-01 | Fixed logger names, added list_accounts.py |
| 0.4 Integration tests | ✅ Done | 2024-12-01 | 23 passed, 5 skipped |
| 1.1 Extend SegmentSequence | ✅ Done | 2024-12-01 | Added render_bytes(), from_bytes(), bytes constructor |
| 1.2 Update imports | ✅ Done | 2024-12-01 | Migrated 5 infrastructure files to Pydantic SegmentSequence |
| 1.3 Validate | ✅ Done | 2024-12-01 | 541 unit + 27 integration tests pass |
| 1.4 Fix capabilities | ✅ Done | 2024-12-01 | Fixed AllowedTransaction.transaction_code access |
| 2.x Remove legacy | ⬜ Not started | | |
| 3.x Test cleanup | ⬜ Not started | | |
| 4.x Documentation | ⬜ Not started | | |

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2024-12-01 | Tests first approach | Provides safety net, documents behavior |
| 2024-12-01 | Extend Pydantic SegmentSequence | Cleaner than maintaining bridge class |
| 2024-12-01 | Fix `SegmentSequenceField` to use legacy parser | Root cause: nested segments in HNVSD were parsed with Pydantic while parent was legacy Container. Fixed by passing `use_pydantic=False` to maintain consistency. |

