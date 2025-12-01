# Legacy Code Deprecation Guide

## Goal

Fully remove the legacy Container-based type system and replace it with the new Pydantic-based protocol layer.

**Target files for removal:**
- `fints/types.py` - Container, Field, SegmentSequence base classes
- `fints/fields.py` - DataElementField, NumericField, etc.
- `fints/formals.py` - 80+ DEG definitions
- `fints/segments/*.py` - 100+ segment definitions
- `fints/parser.py` - Legacy parser/serializer

---

## Current Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        LEGACY SYSTEM                             │
│                                                                  │
│  fints/types.py          fints/fields.py        fints/formals.py │
│  ├── Field              ├── DataElementField   ├── BankIdentifier│
│  ├── Container          ├── NumericField       ├── Amount1       │
│  ├── SegmentSequence    ├── AlphanumericField  ├── Balance2      │
│  └── ContainerMeta      └── CodeField          └── 80+ more DEGs │
│         │                       │                     │          │
│         └───────────────────────┼─────────────────────┘          │
│                                 ▼                                │
│                        fints/segments/*.py                       │
│                        ├── HISAL6, HKSAL7                        │
│                        ├── HNVSK3, HNVSD1                        │
│                        └── 100+ more segments                    │
│                                 │                                │
│                                 ▼                                │
│                          fints/parser.py                         │
│                          ├── FinTS3Parser                        │
│                          └── FinTS3Serializer                    │
│                                 │                                │
│                                 ▼                                │
│                     fints/infrastructure/*                       │
│                     (uses legacy segments)                       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     NEW PYDANTIC SYSTEM                          │
│                                                                  │
│  fints/infrastructure/fints/protocol/                            │
│  ├── types.py           ├── base.py            ├── formals/     │
│  │   ├── FinTSDate      │   ├── FinTSModel     │   ├── enums.py │
│  │   ├── FinTSAmount    │   ├── FinTSSegment   │   ├── amounts.py│
│  │   └── 13 types       │   └── SegmentSequence│   └── 30+ DEGs │
│  │                      │                      │                 │
│  ├── segments/          └── parser.py          │                 │
│  │   ├── HISAL5-7           ├── FinTSParser    │                 │
│  │   ├── HKKAZ5-7           └── FinTSSerializer│                 │
│  │   └── 34 segments                                             │
│  │                                                               │
│  └── NOT YET INTEGRATED with infrastructure                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Migration Phases

### Phase 1: Complete DEG Migration ✅ COMPLETE
**Completed**

Migrated remaining DEGs from `fints/formals.py` to `fints/infrastructure/fints/protocol/formals/`.

**Status:**
- ✅ 30+ DEGs migrated initially (enums, identifiers, amounts, security, responses)
- ✅ TAN DEGs migrated (tan.py) - 7 classes
- ✅ Transaction DEGs migrated (transactions.py) - 10 classes
- ✅ Parameter DEGs migrated (parameters.py) - 8 classes
- ✅ 22 new unit tests added (429 total)

**DEGs to migrate (by category):**

#### 1.1 Account Types
```python
# From fints/formals.py → protocol/formals/accounts.py
- Account2       → AccountIdentifier (done, but verify compatibility)
- Account3       → AccountIdentifier (done)
- KTI1           → AccountInternational (done)
- KTZ1           → AccountInternationalSEPA (done)
```

#### 1.2 TAN-related DEGs
```python
# From fints/formals.py → protocol/formals/tan.py (NEW FILE)
- TANMedia4
- TANMedia5
- TANProcessParameter2
- TANProcessParameter6
- ParameterChallengeClass
- ParameterTwostepTAN (multiple versions)
```

#### 1.3 BPD/UPD DEGs
```python
# From fints/formals.py → protocol/formals/parameters.py (NEW FILE)
- SupportedLanguages2
- SupportedHBCIVersions2
- CommunicationParameter2
- BPD3
- UPD
- AccountInformation6
- AllowedGV
- ParameterPinTan
```

#### 1.4 Transaction DEGs
```python
# From fints/formals.py → protocol/formals/transactions.py (NEW FILE)
- SupportedMessageTypes
- BookedCamtStatements1
- QueryCreditCardStatements2
- BatchTransferParameter1
```

#### 1.5 Miscellaneous
```python
# From fints/formals.py → protocol/formals/misc.py (NEW FILE)
- ReportPeriod2
- PartyIdentification1
```

**Tasks:**
- [ ] Create `protocol/formals/tan.py` with TAN DEGs
- [ ] Create `protocol/formals/parameters.py` with BPD/UPD DEGs
- [ ] Create `protocol/formals/transactions.py` with transaction DEGs
- [ ] Update `protocol/formals/__init__.py` to export all
- [ ] Add unit tests for each new DEG
- [ ] Verify Pydantic DEGs have same wire format as legacy

---

### Phase 2: Complete Segment Migration ✅ COMPLETE
**Completed**

Migrated remaining segments from `fints/segments/*.py` to `fints/infrastructure/fints/protocol/segments/`.

**Status:**
- ✅ 34 segments migrated initially (saldo, accounts, transactions, statements)
- ✅ Dialog segments migrated (dialog.py) - 7 classes: HNHBK3, HNHBS1, HIRMG2, HIRMS2, HKSYN3, HISYN4, HKEND1
- ✅ Message segments migrated (message.py) - 4 classes: HNVSK3, HNVSD1, HNSHK4, HNSHA2
- ✅ Auth segments migrated (auth.py) - 15 classes: HKIDN2, HKVVB3, HKTAN2/6/7, HITAN6/7, HKTAB4/5, HITAB4/5
- ✅ Bank segments migrated (bank.py) - 5 classes: HIBPA3, HIUPA4, HIUPD6, HKKOM4, HIKOM4
- ✅ PIN/TAN segments migrated (pintan.py) - 3 segments + 8 DEGs: HIPINS1, HITANS6, HITANS7
- ✅ 41 new unit tests added initially
- ✅ Transfer segments migrated (transfer.py) - 5 segments + 1 DEG
- ✅ Depot segments migrated (depot.py) - 4 segments + 2 DEGs
- ✅ Journal segments migrated (journal.py) - 6 segments
- ✅ 17 additional tests added (487 unit tests total)

**Segments to migrate (by file):**

#### 2.1 Dialog Segments ✅ DONE
```python
# fints/segments/dialog.py → protocol/segments/dialog.py
- HNHBK3      # ✅ Message header (Nachrichtenkopf)
- HNHBS1      # ✅ Message trailer (Nachrichtenabschluss)
- HIRMG2      # ✅ Global response (Rückmeldung zur Gesamtnachricht)
- HIRMS2      # ✅ Segment response (Rückmeldung zu Segmenten)
- HKSYN3      # ✅ Synchronization request
- HISYN4      # ✅ Synchronization response
- HKEND1      # ✅ Dialog end
- HIBPA3      # ⏳ Bank Parameter Data (Bankparameterdaten)
- HIUPA4      # ⏳ User Parameter Data (Userparameterdaten)
- HIUPD6      # ⏳ Account information
- HIKOM4      # ⏳ Communication access
```

#### 2.2 Message Segments ✅ DONE
```python
# fints/segments/message.py → protocol/segments/message.py
- HNVSK3      # ✅ Encryption header (Verschlüsselungskopf)
- HNVSD1      # ✅ Encryption data (Verschlüsselte Daten)
- HNSHK4      # ✅ Signature header (Signaturkopf)
- HNSHA2      # Signature trailer (Signaturabschluss)
```

#### 2.3 Authentication Segments
```python
# fints/segments/auth.py → protocol/segments/auth.py
- HKIDN2      # Identification (Identifikation)
- HKVVB3      # Processing preparation (Verarbeitungsvorbereitung)
- HKTAN2/6/7  # TAN handling
- HKTAB4/5    # TAN media request
- HITAB4/5    # TAN media response
- HIPINS1     # PIN/TAN info
- HITANS6/7   # TAN procedure info
```

#### 2.4 Bank Info Segments
```python
# fints/segments/bank.py → protocol/segments/bank.py
- HIBPA3      # BPD
- HIKOM4      # Communication
- HISPAS1/3   # SEPA accounts parameter
- HISALS5/6/7 # Balance parameter
- HIKAZS5/6/7 # Transactions parameter
- HIEKAS3/4/5 # Statement parameter
- And many more parameter segments...
```

#### 2.5 Transfer Segments
```python
# fints/segments/transfer.py → protocol/segments/transfer.py
- HKCCS1      # SEPA credit transfer
- HKCCM1      # SEPA collective transfer
- HKCSE1/2    # SEPA standing order
- And more...
```

#### 2.6 Depot Segments
```python
# fints/segments/depot.py → protocol/segments/depot.py
- HKWPD5/6    # Depot statement
- HIWPD5/6    # Depot statement response
```

#### 2.7 Journal Segments
```python
# fints/segments/journal.py → protocol/segments/journal.py
- HKPRO3/4    # Status protocol request
- HIPRO3/4    # Status protocol response
```

**Tasks:**
- [ ] Create dialog segment classes
- [ ] Create message segment classes (security-critical)
- [ ] Create auth segment classes
- [ ] Create bank parameter segment classes
- [ ] Create transfer segment classes
- [ ] Create depot segment classes
- [ ] Create journal segment classes
- [ ] Add unit tests for each segment
- [ ] Add version registries for each segment type

---

### Phase 3: Parser Integration ✅ COMPLETE
**Completed**

Updated the Pydantic parser to work with all migrated segments.

**Status:**
- ✅ 71 segments registered in SegmentRegistry (46 segment types)
- ✅ Auto-registration updated for all new segments
- ✅ 18 parser tests added (505 unit tests total)
- ✅ Round-trip tests for core segments (HNHBK, HNHBS, HKSYN, HKIDN, HKVVB, HIBPA, HIUPA)
- ✅ Nested DEG list parsing works (HIRMG, HIRMS)
- ✅ Empty string handling for None values in wire format

**Completed Tasks:**
- [x] Register all new segments in `SegmentRegistry`
- [x] Add comprehensive parsing tests
- [x] Ensure parser handles nested DEGs correctly
- [x] Ensure parser handles repeated fields (lists)
- [x] Fix None → empty string conversion for required string fields

**Test with real data:**
```python
# Test parsing actual bank responses
def test_parse_real_hibpa():
    raw = b"HIBPA:5:3+12+280:12345678+Testbank+..."
    parser = FinTSParser()
    segments = parser.parse_message(raw)
    hibpa = segments.find_segment_first("HIBPA")
    assert hibpa.bank_name == "Testbank"
```

---

### Phase 4: Infrastructure Migration ✅ COMPLETE (Enum Fix)
**Completed**

Fixed Pydantic enum compatibility and updated infrastructure imports.

**Key Fix: `FinTSEnum` base class**
Added `FinTSEnum` and `FinTSIntEnum` base classes that return value from `__str__`:
- Before: `str(SynchronizationMode.NEW_SYSTEM_ID)` → `'SynchronizationMode.NEW_SYSTEM_ID'`
- After: `str(SynchronizationMode.NEW_SYSTEM_ID)` → `'0'` (matches legacy behavior)

**Status:**
- ✅ Protocol package exports all 71 segments (46 types)
- ✅ Protocol enums now compatible with legacy field parsing
- ✅ Simple enum imports can use protocol layer (SynchronizationMode, StatementFormat, etc.)
- ⚠️ DEGs used as segment parameters must still use legacy (SupportedMessageTypes, BankIdentifier)
- ⚠️ Legacy segments still in use (requires full segment migration to change)
- ✅ ParameterStore used from new protocol layer

**What's Migrated (uses new protocol):**
- Enums: CUSTOMER_ID_ANONYMOUS, SynchronizationMode, StatementFormat, Confirmation
- Enums: TANMediaClass4, TANMediaType2, TANUsageOption
- Types: ParameterStore

**What Uses Legacy (needs full segment migration):**
- DEGs: SupportedMessageTypes, BankIdentifier, Language2, SystemIDStatus
- DEGs: Security DEGs (EncryptionAlgorithm, KeyName, etc.)
- All segments: HKSAL*, HISAL*, HKKAZ*, HIKAZ*, etc.

**Reason Legacy DEGs/Segments Remain:**
- Legacy segments expect Container-based DEG fields
- Pydantic DEGs are constructed differently (`field=value` vs positional)
- Full migration requires updating all segment construction code

#### 4.1 Update Message Handling
```python
# fints/message.py - Replace legacy SegmentSequence
# Current:
class FinTSMessage(SegmentSequence):  # Legacy
    ...

# Target:
from fints.infrastructure.fints.protocol import SegmentSequence
class FinTSMessage(SegmentSequence):  # Pydantic
    ...
```

#### 4.2 Update Dialog Layer
```python
# fints/infrastructure/fints/dialog/*.py
# Replace imports:
# FROM: from fints.formals import BankIdentifier, ...
# TO:   from fints.infrastructure.fints.protocol import BankIdentifier, ...
```

#### 4.3 Update Operations Layer
```python
# fints/infrastructure/fints/operations/*.py
# Replace segment usage:
# FROM: from fints.segments.saldo import HKSAL7
# TO:   from fints.infrastructure.fints.protocol import HKSAL7
```

#### 4.4 Update Auth Layer
```python
# fints/infrastructure/fints/auth/*.py
# Replace security segment usage
```

**Tasks:**
- [ ] Update `fints/message.py` to use Pydantic SegmentSequence
- [ ] Update dialog layer imports
- [ ] Update operations layer imports
- [ ] Update auth layer imports
- [ ] Update adapters layer imports
- [ ] Run integration tests after each update

---

### Phase 5: Legacy File Removal ⏳
**Estimated effort: 1-2 days**

Remove deprecated files after migration is complete.

#### 5.1 Pre-removal Checklist
- [ ] All DEGs migrated and tested
- [ ] All segments migrated and tested
- [ ] All infrastructure updated
- [ ] All unit tests pass (400+)
- [ ] All integration tests pass (15+)
- [ ] No imports from legacy files remain

#### 5.2 File Removal Order

```bash
# Step 1: Remove legacy segments (depends on formals)
rm -rf fints/segments/

# Step 2: Remove legacy parser (depends on segments)
rm fints/parser.py

# Step 3: Remove legacy formals (depends on types/fields)
rm fints/formals.py

# Step 4: Remove legacy field definitions (depends on types)
rm fints/fields.py

# Step 5: Remove legacy type system
rm fints/types.py
```

#### 5.3 Post-removal Tasks
- [ ] Update `fints/__init__.py` to export from new location
- [ ] Update any remaining imports
- [ ] Run full test suite
- [ ] Update documentation

---

### Phase 6: Cleanup and Documentation ⏳
**Estimated effort: 1 day**

#### 6.1 Move Protocol Layer
```bash
# Consider moving protocol to top-level for cleaner imports
fints/infrastructure/fints/protocol/ → fints/protocol/
```

#### 6.2 Update Public API
```python
# fints/__init__.py
from fints.protocol import (
    FinTSParser,
    FinTSSerializer,
    SegmentSequence,
    # ... key exports
)
```

#### 6.3 Documentation Updates
- [ ] Update README with new import paths
- [ ] Update docstrings
- [ ] Add migration guide for external users
- [ ] Update type hints

---

## Dependency Graph for Removal

```
                    ┌─────────────┐
                    │ fints/types │
                    │   .py       │
                    └──────┬──────┘
                           │ used by
                           ▼
                    ┌─────────────┐
                    │fints/fields │
                    │   .py       │
                    └──────┬──────┘
                           │ used by
                           ▼
                    ┌─────────────┐
                    │fints/formals│
                    │   .py       │
                    └──────┬──────┘
                           │ used by
              ┌────────────┼────────────┐
              ▼            ▼            ▼
       ┌───────────┐ ┌───────────┐ ┌───────────┐
       │ segments/ │ │  message  │ │  parser   │
       │   *.py    │ │   .py     │ │   .py     │
       └─────┬─────┘ └─────┬─────┘ └─────┬─────┘
             │             │             │
             └─────────────┼─────────────┘
                           │ used by
                           ▼
                  ┌─────────────────┐
                  │ infrastructure/ │
                  │      *.py       │
                  └─────────────────┘

REMOVAL ORDER (bottom to top):
1. Update infrastructure → use Pydantic
2. Remove segments/*.py
3. Remove parser.py
4. Remove formals.py
5. Remove fields.py
6. Remove types.py
```

---

## Estimated Total Effort

| Phase | Description | Days |
|-------|-------------|------|
| 1 | Complete DEG Migration | 2-3 |
| 2 | Complete Segment Migration | 3-5 |
| 3 | Parser Integration | 2-3 |
| 4 | Infrastructure Migration | 5-7 |
| 5 | Legacy File Removal | 1-2 |
| 6 | Cleanup and Documentation | 1 |
| **Total** | | **14-21 days** |

---

## Risk Mitigation

1. **Test after each phase** - Run full test suite
2. **Feature flags** - Allow switching between legacy and Pydantic
3. **Incremental commits** - One segment/DEG type per commit
4. **Integration test coverage** - Ensure real bank communication works
5. **Rollback plan** - Keep legacy files until fully validated

---

## Quick Reference: Import Changes

```python
# BEFORE (Legacy)
from fints.types import Container, SegmentSequence
from fints.fields import DataElementField, NumericField
from fints.formals import BankIdentifier, Amount1, SynchronizationMode
from fints.segments.saldo import HISAL6
from fints.parser import FinTS3Parser

# AFTER (Pydantic)
from fints.infrastructure.fints.protocol import (
    FinTSModel,
    SegmentSequence,
    FinTSNumeric,
    FinTSAlphanumeric,
    BankIdentifier,
    Amount,
    SynchronizationMode,
    HISAL6,
    FinTSParser,
)
```

---

## Progress Tracking

Use this checklist to track progress:

### Phase 1: DEG Migration ✅
- [x] tan.py created (TANMedia4/5, ChallengeValidUntil, etc.)
- [x] parameters.py created (SupportedLanguages, CommunicationParameter, etc.)
- [x] transactions.py created (SupportedMessageTypes, BatchTransferParameter, etc.)
- [x] All DEGs have unit tests (22 new tests)
- [ ] Wire format verified (pending integration)

### Phase 2: Segment Migration ✅ COMPLETE
- [x] dialog.py segments (HNHBK3, HNHBS1, HIRMG2, HIRMS2, HKSYN3, HISYN4, HKEND1)
- [x] message.py segments (HNVSK3, HNVSD1, HNSHK4, HNSHA2)
- [x] auth.py segments (HKIDN2, HKVVB3, HKTAN2/6/7, HITAN6/7, HKTAB4/5, HITAB4/5)
- [x] bank.py segments (HIBPA3, HIUPA4, HIUPD6, HKKOM4, HIKOM4)
- [x] pintan.py segments (HIPINS1, HITANS6, HITANS7)
- [x] transfer.py segments (HKCCS1, HKIPZ1, HKCCM1, HKIPM1, HICCMS1)
- [x] depot.py segments (HKWPD5/6, HIWPD5/6)
- [x] journal.py segments (HKPRO3/4, HIPRO3/4, HIPROS3/4)
- [x] All segments have unit tests (58 new tests, 487 total)

### Phase 3: Parser ✅ COMPLETE
- [x] All segments registered (71 segments, 46 types)
- [x] Round-trip tests for core segments
- [x] Nested DEG list parsing (HIRMG, HIRMS)
- [x] Empty string handling for None values

### Phase 4: Infrastructure ✅ COMPLETE (Partial)
- [x] `FinTSEnum` base class added (fixes `str()` compatibility)
- [x] `FinTSIntEnum` base class added
- [x] Enum imports updated where compatible
- [x] Integration tests pass (520 total)
- ⏳ **BLOCKED**: Full segment migration requires:
  - [ ] Update all segment construction to Pydantic API
  - [ ] Update all DEG construction to Pydantic API
  - [ ] Update dialog message building
  - [ ] Update message security wrapping

### Phase 5: Removal
- [ ] segments/ removed
- [ ] parser.py removed
- [ ] formals.py removed
- [ ] fields.py removed
- [ ] types.py removed

### Phase 6: Cleanup
- [ ] Imports updated
- [ ] Documentation updated
- [ ] README updated

