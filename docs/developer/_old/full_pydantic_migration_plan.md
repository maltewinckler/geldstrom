# Full Pydantic Migration Plan

## Executive Summary

This document outlines the complete plan to migrate the FinTS protocol layer from the legacy Container-based system to Pydantic models, enabling full removal of legacy code.

## Current State (December 2025)

### Completed ✅

1. **Pydantic Protocol Infrastructure**
   - `fints/infrastructure/fints/protocol/base.py` - FinTSModel, FinTSSegment, SegmentSequence
   - `fints/infrastructure/fints/protocol/types.py` - All annotated types (FinTSDate, FinTSAmount, etc.)
   - `fints/infrastructure/fints/protocol/parser.py` - FinTSParser, FinTSSerializer, SegmentRegistry

2. **Core DEGs** (`protocol/formals/`)
   - `enums.py` - 40+ enums including TAN-related enums
   - `identifiers.py` - BankIdentifier, AccountIdentifier, AccountInternational
   - `amounts.py` - Amount, Balance, BalanceSimple, Timestamp
   - `security.py` - SecurityProfile, KeyName, Certificate, etc.
   - `responses.py` - Response, ReferenceMessage
   - `tan.py` - TANMedia, ChallengeValidUntil, ResponseHHDUC, etc.
   - `transactions.py` - Transaction-related DEGs
   - `parameters.py` - BPD/UPD-related DEGs

3. **All Segment Definitions** (`protocol/segments/`)
   - `dialog.py` - HNHBK, HNHBS, HIRMG, HIRMS, HKSYN, HISYN, HKEND
   - `message.py` - HNVSK, HNVSD, HNSHK, HNSHA
   - `auth.py` - HKIDN, HKVVB, HKTAN, HITAN, HKTAB, HITAB
   - `bank.py` - HIBPA, HIUPA, HIUPD, HKKOM, HIKOM
   - `pintan.py` - HIPINS1, HITANS1-7 (all versions now implemented)
   - `transfer.py` - HKCCS, HKCCM, HKIPZ, HKIPM, HICCMS
   - `depot.py` - HKWPD, HIWPD
   - `journal.py` - HKPRO, HIPRO, HIPROS
   - `saldo.py` - HKSAL5-7, HISAL5-7
   - `accounts.py` - HKSPA1, HISPA1
   - `transactions.py` - HKKAZ5-7, HIKAZ5-7, HKCAZ1, HICAZ1
   - `statements.py` - HKEKA3-5, HIEKA3-5, HKKAU1-2, HIKAU1-2
   - `informational.py` - HIAZSS1, HIVISS1 (stub implementations)

4. **Outgoing Messages**
   - All request segments use Pydantic models
   - Serialization via `FinTSSerializer`

### Recently Completed ✅

1. **Pydantic Parser Feature Flag** (December 2025)
   - Added `USE_PYDANTIC_PARSER` flag in `fints/types.py`
   - `SegmentSequence` can now use Pydantic parser via `use_pydantic=True`
   - Updated `parameters.py` to use `FinTSSerializer` instead of legacy

### Remaining Work 🔲

1. **Test with Real Bank Data**
   - Enable `USE_PYDANTIC_PARSER = True` in test environment
   - Run integration tests with multiple banks (Triodos, DKB, etc.)
   - Fix any parsing issues discovered

2. **Legacy Code Removal** (after validation)
   - `fints/parser.py` - Deprecated, remove after Pydantic parser validated
   - `fints/segments/*.py` - Deprecated
   - `fints/formals.py` - Deprecated
   - `fints/fields.py` - Deprecated
   - `fints/types.py` - Deprecate remaining Container classes

---

## How to Enable Pydantic Parser

The Pydantic parser can be enabled via a feature flag. This allows gradual migration and testing.

### Global Flag

```python
# In fints/types.py
import fints.types
fints.types.USE_PYDANTIC_PARSER = True
```

### Per-instance Flag

```python
from fints.types import SegmentSequence

# Parse with Pydantic parser
seq = SegmentSequence(raw_bytes, use_pydantic=True)

# Parse with legacy parser (default)
seq = SegmentSequence(raw_bytes, use_pydantic=False)
```

### In Tests

```python
import fints.types

# Enable for all tests in a module
@pytest.fixture(autouse=True)
def enable_pydantic_parser():
    original = fints.types.USE_PYDANTIC_PARSER
    fints.types.USE_PYDANTIC_PARSER = True
    yield
    fints.types.USE_PYDANTIC_PARSER = original
```

---

## Migration Strategy

### Phase 1: Parser Robustness (Current Focus)

**Goal**: Make Pydantic parser handle all bank response variations

**Tasks**:

1. **Handle Flat vs Nested DEG Data**
   ```python
   # Some banks send DEGs as nested lists:
   [['280', '12345678'], 'account_num']

   # Others send them flat:
   ['280', '12345678', 'account_num']
   ```

   Current `from_wire_list` handles this via `_count_model_fields`, but needs:
   - Better handling of optional fields in the middle of structures
   - More lenient parsing when field counts don't match

2. **Validation Tolerance**

   Add configuration for strict vs lenient parsing:
   ```python
   parser = FinTSParser(
       robust_mode=True,        # Warn instead of raise
       strict_validation=False, # Accept partial data
   )
   ```

3. **Unknown Segment Fallback**

   Create a generic segment that captures any data:
   ```python
   class UnknownSegment(FinTSSegment):
       raw_data: list[Any]
   ```

### Phase 2: Switch Response Parsing

**Goal**: Use Pydantic parser for all incoming messages

**Tasks**:

1. Update `ResponseProcessor` in `dialog/responses.py`:
   ```python
   # From:
   segments = fints.parser.parse_message(raw_bytes)

   # To:
   parser = FinTSParser(robust_mode=True)
   segments = parser.parse_message(raw_bytes)
   ```

2. Update segment access patterns:
   ```python
   # Old pattern (legacy segments):
   for seg in response.segments.find_segment_first('HISAL'):
       balance = seg.balance_booked.amount

   # New pattern (Pydantic segments):
   for seg in response.find_segments('HISAL'):
       balance = seg.balance_booked.signed_amount
   ```

3. Update all adapters that read response data:
   - `adapters/accounts.py`
   - `adapters/balances.py`
   - `adapters/transactions.py`
   - `adapters/statements.py`

### Phase 3: Remove Legacy Code

**Goal**: Delete all deprecated legacy files

**Order of Removal**:

1. **fints/parser.py** - After Phase 2 is complete
2. **fints/segments/*.py** - Move any still-used re-exports
3. **fints/formals.py** - Move any still-used re-exports
4. **fints/fields.py** - Should have no more consumers
5. **fints/types.py** - Should have no more consumers

**Deprecation Steps**:

```python
# Step 1: Add deprecation warnings (already done)
# Step 2: Remove internal usage
# Step 3: Keep re-exports for 1 release
# Step 4: Remove files
```

---

## Test Strategy

### Current Test Coverage

| Area | Tests | Status |
|------|-------|--------|
| `protocol/types.py` | 85 tests | ✅ |
| `protocol/base.py` | 23 tests | ✅ |
| `protocol/formals/` | 44 tests | ✅ |
| `protocol/segments/` | 120 tests | ✅ |
| `protocol/parser.py` | 27 tests | ✅ |

### Additional Tests Needed

1. **Round-trip parsing tests with real bank data**
   - Record actual bank responses
   - Parse → serialize → parse should match

2. **Cross-bank compatibility tests**
   - Test with different banks (Triodos, DKB, etc.)
   - Each bank has slight variations in format

3. **Error case coverage**
   - Missing required fields
   - Invalid enum values
   - Malformed data

---

## Segment Coverage Summary

### Full Implementations ✅

| Segment | Versions | Notes |
|---------|----------|-------|
| HNHBK | 3 | Message header |
| HNHBS | 1 | Message trailer |
| HIRMG | 2 | Message response |
| HIRMS | 2 | Segment response |
| HNVSK | 3 | Encryption container |
| HNVSD | 1 | Encrypted data |
| HNSHK | 4 | Signature header |
| HNSHA | 2 | Signature trailer |
| HKIDN | 2 | Identification |
| HKVVB | 3 | Processing preparation |
| HKTAN | 2, 6, 7 | TAN request |
| HITAN | 6, 7 | TAN response |
| HKTAB | 4, 5 | TAN media request |
| HITAB | 4, 5 | TAN media response |
| HIBPA | 3 | Bank parameters |
| HIUPA | 4 | User parameters |
| HIUPD | 6 | User data |
| HKKOM | 4 | Communication request |
| HIKOM | 4 | Communication response |
| HIPINS | 1 | PIN/TAN info |
| HITANS | 1-7 | TAN parameters (all versions) |
| HKSAL | 5-7 | Balance request |
| HISAL | 5-7 | Balance response |
| HKSPA | 1 | SEPA accounts request |
| HISPA | 1 | SEPA accounts response |
| HKKAZ | 5-7 | MT940 transactions |
| HIKAZ | 5-7 | MT940 response |
| HKCAZ | 1 | CAMT transactions |
| HICAZ | 1 | CAMT response |
| HKEKA | 3-5 | Statements request |
| HIEKA | 3-5 | Statements response |
| HKKAU | 1-2 | Statement overview |
| HIKAU | 1-2 | Statement overview response |
| HKCCS | 1 | SEPA transfer |
| HKCCM | 1 | SEPA batch transfer |
| HKIPZ | 1 | Instant payment |
| HKIPM | 1 | Instant batch payment |
| HICCMS | 1 | Transfer parameters |
| HKWPD | 5-6 | Portfolio request |
| HIWPD | 5-6 | Portfolio response |
| HKPRO | 3-4 | Protocol request |
| HIPRO | 3-4 | Protocol response |
| HIPROS | 3-4 | Protocol parameters |
| HIAZS | 1 | Auth security (stub) |
| HIVIS | 1 | Visualization (stub) |
| HKSYN | 3 | Sync request |
| HISYN | 4 | Sync response |
| HKEND | 1 | Dialog end |

### Total: 70+ segment versions implemented

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Bank compatibility issues | High | Extensive testing with multiple banks |
| Performance regression | Medium | Benchmark critical paths |
| Breaking existing integrations | High | Gradual rollout with deprecation warnings |
| Incomplete segment coverage | Low | Stub implementations for unknown segments |

---

## Timeline Estimate

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Parser Robustness | 1 week | None |
| Phase 2: Switch Response Parsing | 2 weeks | Phase 1 |
| Phase 3: Remove Legacy Code | 1 week | Phase 2, testing |

**Total**: ~4 weeks

---

## Success Criteria

1. All unit tests pass (500+)
2. All integration tests pass (15+)
3. No legacy parser imports in infrastructure code
4. No runtime deprecation warnings from internal code
5. Performance within 10% of legacy system

---

## Appendix: Code Examples

### Before (Legacy)

```python
from fints import formals
from fints.parser import parse_message

response = parse_message(raw_bytes)
for seg in response.find_segments('HISAL'):
    balance = seg.balance_booked.amount
    currency = seg.currency
```

### After (Pydantic)

```python
from fints.infrastructure.fints.protocol import (
    FinTSParser,
    HISAL6,
)

parser = FinTSParser()
segments = parser.parse_message(raw_bytes)

for seg in segments.find_segments('HISAL'):
    balance = seg.balance_booked.signed_amount
    currency = seg.currency
```

