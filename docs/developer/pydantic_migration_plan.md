# Pydantic Migration Plan

## Goal

Replace the descriptor-based `Field`/`Container` system in `fints/types.py` and `fints/fields.py` with Pydantic models while:
1. **Avoiding code repetition** (DRY principle)
2. **Maintaining high code quality** and readability
3. **Preserving backward compatibility** during migration
4. **Enabling gradual rollout** with feature flags

---

## Current State Analysis

### Files to Migrate

| File | Lines | Classes | Priority |
|------|-------|---------|----------|
| `fints/types.py` | 439 | 6 classes | High |
| `fints/fields.py` | 316 | 25+ field types | High |
| `fints/formals.py` | 1080 | 80+ DEGs/enums | Medium |
| `fints/segments/*.py` | ~1500 | 100+ segments | Low |

### Key Observations

1. **Field types are repetitive** - Many share parsing/rendering logic
2. **Segments follow patterns** - Request/Response pairs, versioning
3. **DEGs nest deeply** - But follow predictable structures
4. **Wire format rules are finite** - ~10 core transformations

---

## Architecture: Reusable Components

### Layer 1: FinTS Type Annotations (Shared)

Create reusable type annotations with built-in validation:

```python
# fints/protocol/types.py
from typing import Annotated
from decimal import Decimal
from datetime import date, time
from pydantic import Field, BeforeValidator, PlainSerializer

# === Core Validators (reusable) ===

def parse_fints_date(v) -> date:
    """YYYYMMDD → date"""
    if isinstance(v, date):
        return v
    if isinstance(v, str) and len(v) == 8:
        return date(int(v[:4]), int(v[4:6]), int(v[6:8]))
    raise ValueError(f"Invalid FinTS date: {v}")

def parse_fints_time(v) -> time:
    """HHMMSS → time"""
    if isinstance(v, time):
        return v
    if isinstance(v, str) and len(v) == 6:
        return time(int(v[:2]), int(v[2:4]), int(v[4:6]))
    raise ValueError(f"Invalid FinTS time: {v}")

def parse_fints_amount(v) -> Decimal:
    """German decimal (123,45) → Decimal"""
    if isinstance(v, Decimal):
        return v
    if isinstance(v, (int, float)):
        return Decimal(str(v))
    if isinstance(v, str):
        return Decimal(v.replace(',', '.'))
    raise ValueError(f"Invalid FinTS amount: {v}")

def parse_fints_bool(v) -> bool:
    """J/N → bool"""
    if isinstance(v, bool):
        return v
    if v == 'J':
        return True
    if v == 'N':
        return False
    raise ValueError(f"Invalid FinTS boolean: {v}")

# === Serializers (reusable) ===

def serialize_fints_date(v: date) -> str:
    return v.strftime('%Y%m%d')

def serialize_fints_time(v: time) -> str:
    return v.strftime('%H%M%S')

def serialize_fints_amount(v: Decimal) -> str:
    return str(v).replace('.', ',')

def serialize_fints_bool(v: bool) -> str:
    return 'J' if v else 'N'

# === Annotated Types (used everywhere) ===

FinTSDate = Annotated[
    date,
    BeforeValidator(parse_fints_date),
    PlainSerializer(serialize_fints_date),
    Field(description="FinTS date (YYYYMMDD)"),
]

FinTSTime = Annotated[
    time,
    BeforeValidator(parse_fints_time),
    PlainSerializer(serialize_fints_time),
    Field(description="FinTS time (HHMMSS)"),
]

FinTSAmount = Annotated[
    Decimal,
    BeforeValidator(parse_fints_amount),
    PlainSerializer(serialize_fints_amount),
    Field(description="FinTS amount (German decimal)"),
]

FinTSBool = Annotated[
    bool,
    BeforeValidator(parse_fints_bool),
    PlainSerializer(serialize_fints_bool),
    Field(description="FinTS boolean (J/N)"),
]

FinTSNumeric = Annotated[
    int,
    BeforeValidator(lambda v: int(v) if isinstance(v, str) else v),
    Field(description="FinTS numeric"),
]

FinTSAlphanumeric = Annotated[
    str,
    Field(description="FinTS alphanumeric"),
]

FinTSBinary = Annotated[
    bytes,
    Field(description="FinTS binary data"),
]

FinTSCurrency = Annotated[
    str,
    Field(min_length=3, max_length=3, description="ISO 4217 currency code"),
]

FinTSCountry = Annotated[
    str,
    Field(min_length=3, max_length=3, pattern=r'^\d{3}$', description="ISO 3166 numeric country"),
]

FinTSID = Annotated[
    str,
    Field(max_length=30, description="FinTS identifier"),
]
```

### Layer 2: Base Models (Shared Behavior)

```python
# fints/protocol/base.py
from pydantic import BaseModel, ConfigDict
from typing import ClassVar, Iterator, Any

class FinTSModel(BaseModel):
    """Base class for all FinTS protocol models."""

    model_config = ConfigDict(
        # Strict validation
        strict=False,  # Allow coercion via validators
        # Extra fields handling
        extra='ignore',  # Ignore unknown fields from bank
        # Serialization
        ser_json_inf_nan='constants',
    )

    @classmethod
    def from_wire_list(cls, data: list[Any]) -> 'FinTSModel':
        """Parse from FinTS DEG/segment data list."""
        field_names = list(cls.model_fields.keys())
        kwargs = {}
        for i, value in enumerate(data):
            if i < len(field_names):
                kwargs[field_names[i]] = value
        return cls(**kwargs)

    def to_wire_list(self) -> list[Any]:
        """Export as FinTS DEG/segment data list."""
        return [
            getattr(self, name)
            for name in self.model_fields.keys()
        ]


class FinTSDataElementGroup(FinTSModel):
    """Base for Data Element Groups (DEGs)."""
    pass


class FinTSSegment(FinTSModel):
    """Base for FinTS segments."""

    # Class-level metadata
    SEGMENT_TYPE: ClassVar[str] = ""
    SEGMENT_VERSION: ClassVar[int] = 0

    # Segment header (always present)
    header: 'SegmentHeader'

    @classmethod
    def segment_id(cls) -> str:
        """Returns e.g., 'HISAL6'."""
        return f"{cls.SEGMENT_TYPE}{cls.SEGMENT_VERSION}"


class SegmentSequence(FinTSModel):
    """Collection of segments with query methods."""

    segments: list[FinTSSegment] = []

    def find_segments(
        self,
        query: str | type | list | None = None,
        version: int | list[int] | None = None,
        callback: callable | None = None,
    ) -> Iterator[FinTSSegment]:
        """Find segments matching criteria."""
        # Normalize query
        if query is None:
            queries = []
        elif isinstance(query, (str, type)):
            queries = [query]
        else:
            queries = list(query)

        # Normalize version
        if version is None:
            versions = []
        elif isinstance(version, int):
            versions = [version]
        else:
            versions = list(version)

        for seg in self.segments:
            # Check type match
            if queries:
                type_match = any(
                    (isinstance(seg, q) if isinstance(q, type)
                     else seg.SEGMENT_TYPE == q)
                    for q in queries
                )
                if not type_match:
                    continue

            # Check version match
            if versions and seg.SEGMENT_VERSION not in versions:
                continue

            # Check callback
            if callback and not callback(seg):
                continue

            yield seg

    def find_segment_first(self, **kwargs) -> FinTSSegment | None:
        """Find first matching segment."""
        for seg in self.find_segments(**kwargs):
            return seg
        return None

    def find_segment_highest_version(self, **kwargs) -> FinTSSegment | None:
        """Find segment with highest version."""
        highest = None
        for seg in self.find_segments(**kwargs):
            if highest is None or seg.SEGMENT_VERSION > highest.SEGMENT_VERSION:
                highest = seg
        return highest
```

### Layer 3: Concrete DEGs (Minimal Repetition)

```python
# fints/protocol/formals/identifiers.py
from fints.protocol.base import FinTSDataElementGroup
from fints.protocol.types import FinTSCountry, FinTSAlphanumeric, FinTSID

class BankIdentifier(FinTSDataElementGroup):
    """Kreditinstitutskennung."""
    country_identifier: FinTSCountry
    bank_code: FinTSAlphanumeric


class AccountIdentifier(FinTSDataElementGroup):
    """Kontoverbindung."""
    account_number: FinTSID
    subaccount_number: FinTSID | None = None
    bank_identifier: BankIdentifier


# fints/protocol/formals/amounts.py
from fints.protocol.base import FinTSDataElementGroup
from fints.protocol.types import FinTSAmount, FinTSCurrency

class Amount(FinTSDataElementGroup):
    """Betrag."""
    amount: FinTSAmount
    currency: FinTSCurrency


# fints/protocol/formals/balances.py
from typing import Literal
from fints.protocol.base import FinTSDataElementGroup
from fints.protocol.types import FinTSDate, FinTSTime

class Balance(FinTSDataElementGroup):
    """Saldo."""
    credit_debit: Literal['C', 'D']
    amount: Amount
    date: FinTSDate
    time: FinTSTime | None = None

    @property
    def signed_amount(self) -> Decimal:
        """Amount with sign based on credit/debit."""
        amt = self.amount.amount
        return amt if self.credit_debit == 'C' else -amt
```

### Layer 4: Segments (Factory Pattern for Versions)

```python
# fints/protocol/segments/saldo.py
from typing import ClassVar
from fints.protocol.base import FinTSSegment
from fints.protocol.formals import AccountIdentifier, Balance, Amount
from fints.protocol.types import FinTSAlphanumeric, FinTSCurrency, FinTSDate


class HISALBase(FinTSSegment):
    """Base for balance response segments."""
    SEGMENT_TYPE: ClassVar[str] = "HISAL"

    account_product: FinTSAlphanumeric
    currency: FinTSCurrency
    balance_booked: Balance
    balance_pending: Balance | None = None
    line_of_credit: Amount | None = None
    available_amount: Amount | None = None


class HISAL5(HISALBase):
    """Saldenrückmeldung, version 5."""
    SEGMENT_VERSION: ClassVar[int] = 5
    account: AccountIdentifier  # Version 5 uses simple account


class HISAL6(HISALBase):
    """Saldenrückmeldung, version 6."""
    SEGMENT_VERSION: ClassVar[int] = 6
    account: AccountIdentifier
    used_amount: Amount | None = None
    overdraft: Amount | None = None
    booking_date: FinTSDate | None = None


class HISAL7(HISALBase):
    """Saldenrückmeldung, version 7."""
    SEGMENT_VERSION: ClassVar[int] = 7
    account: AccountIdentifier  # KTI1 (international)
    used_amount: Amount | None = None
    overdraft: Amount | None = None
    booking_date: FinTSDate | None = None


# Segment registry for parser
HISAL_VERSIONS = {
    5: HISAL5,
    6: HISAL6,
    7: HISAL7,
}

def get_hisal_class(version: int) -> type[HISALBase]:
    """Get HISAL class for version."""
    return HISAL_VERSIONS.get(version, HISAL7)
```

---

## Migration Phases

### Phase 1: Foundation (Week 1-2) ✅ COMPLETE
**Create reusable infrastructure without breaking existing code.**

```
fints/infrastructure/fints/protocol/    # Extended existing directory
├── __init__.py              # Updated with new exports
├── parameters.py            # Existing - BPD/UPD management
├── types.py                 # NEW - Annotated types (FinTSDate, etc.)
└── base.py                  # NEW - FinTSModel, FinTSSegment, SegmentSequence
```

**Tasks:**
- [ ] Create `fints/protocol/types.py` with all Annotated types
- [ ] Create `fints/protocol/base.py` with base models
- [ ] Add comprehensive tests for type parsing/serialization
- [ ] Document the new type system

**Deliverable:** Reusable Pydantic foundation, zero breaking changes.

---

### Phase 2: Core DEGs (Week 3-4) ✅ COMPLETE
**Migrate the most-used Data Element Groups.**

```
fints/infrastructure/fints/protocol/formals/    # NEW directory
├── __init__.py              # Exports all DEGs and enums
├── enums.py                 # 20+ enums (SecurityMethod, CreditDebit, etc.)
├── identifiers.py           # BankIdentifier, AccountIdentifier, etc.
├── amounts.py               # Amount, Balance, Timestamp
├── security.py              # SecurityProfile, KeyName, etc.
└── responses.py             # Response, ReferenceMessage
```

**Completed:**
- [x] Migrate `BankIdentifier`, `AccountIdentifier`, `AccountInternational`
- [x] Migrate `Amount`, `Balance`, `BalanceSimple`, `Timestamp`
- [x] Migrate security-related DEGs (`SecurityProfile`, `KeyName`, etc.)
- [x] Migrate response DEGs (`Response`, `ReferenceMessage`)
- [x] Create comprehensive enums module (20+ enums)
- [x] Add 44 unit tests for all new DEGs

**Backward Compatibility:**
```python
class BankIdentifier(FinTSDataElementGroup):
    # ... Pydantic definition ...

    @classmethod
    def from_legacy(cls, legacy: 'formals.BankIdentifier') -> 'BankIdentifier':
        """Convert from old Container-based BankIdentifier."""
        return cls(
            country_identifier=legacy.country_identifier,
            bank_code=legacy.bank_code,
        )

    def to_legacy(self) -> 'formals.BankIdentifier':
        """Convert to old Container-based BankIdentifier."""
        from fints import formals
        return formals.BankIdentifier(
            country_identifier=self.country_identifier,
            bank_code=self.bank_code,
        )
```

---

### Phase 3: Response Segments (Week 5-6) ✅ COMPLETE
**Migrate bank response segments (read-only, lower risk).**

```
fints/infrastructure/fints/protocol/segments/
├── __init__.py              # Exports all segments
├── saldo.py                 # HKSAL5-7, HISAL5-7 with version registries
└── accounts.py              # HKSPA1, HISPA1
```

**Completed:**
- [x] Migrate balance request segments (HKSAL5, HKSAL6, HKSAL7)
- [x] Migrate balance response segments (HISAL5, HISAL6, HISAL7)
- [x] Migrate account segments (HKSPA1, HISPA1)
- [x] Create version registries (HKSAL_VERSIONS, HISAL_VERSIONS)
- [x] Add 16 unit tests for all segments

---

### Phase 4: Request Segments (Week 7-8) ✅ COMPLETE
**Migrate transaction and statement request/response segments.**

```
fints/infrastructure/fints/protocol/segments/
├── __init__.py        # Exports all 34 segment classes
├── saldo.py           # Balance segments (6 classes)
├── accounts.py        # Account segments (2 classes)
├── transactions.py    # Transaction segments (12 classes)
└── statements.py      # Statement segments (14 classes)
```

**Completed:**
- [x] Migrate MT940 transaction segments (HKKAZ5-7, HIKAZ5-7)
- [x] Migrate CAMT transaction segments (HKCAZ1, HICAZ1)
- [x] Migrate statement segments (HKEKA3-5, HIEKA3-5)
- [x] Migrate statement overview segments (HKKAU1-2, HIKAU1-2)
- [x] Add supporting DEGs (ReportPeriod)
- [x] Add enums (StatementFormat, Confirmation)
- [x] Add 17 unit tests for new segments (33 total for Phase 3+4)

---

### Phase 5: Parser Integration (Week 9-10) ✅ COMPLETE
**Rewrite parser to output Pydantic directly.**

```
fints/infrastructure/fints/protocol/
└── parser.py         # FinTSParser, SegmentRegistry, FinTSSerializer
```

**Components:**
- `ParserState` / `Token`: Tokenizer for FinTS wire format
- `SegmentRegistry`: Maps segment type+version to Pydantic classes
- `FinTSParser`: Parses wire bytes into Pydantic segments
- `FinTSSerializer`: Serializes Pydantic segments back to wire format

**Usage:**
```python
from fints.infrastructure.fints.protocol import (
    FinTSParser, SegmentRegistry, FinTSSerializer
)

# Parse a message
parser = FinTSParser()
segments = parser.parse_message(raw_bytes)

# Access parsed segments
for seg in segments.find_segments("HISAL"):
    print(f"Balance: {seg.balance_booked.signed_amount}")

# Serialize back
serializer = FinTSSerializer()
wire_bytes = serializer.serialize_message(segments)
```

**Completed:**
- [x] Create `parser.py` with tokenizer, parser, and serializer
- [x] Implement `SegmentRegistry` with auto-registration
- [x] Implement robust mode (warnings vs exceptions)
- [x] Implement wire format explode/implode round-trip
- [x] Add 27 unit tests for parser components

---

### Phase 6: Cleanup (Week 11-12) ✅ COMPLETE
**Add deprecation notices and verify coexistence.**

**Situation:**
The legacy code (`fints/types.py`, `fints/fields.py`, `fints/formals.py`, `fints/segments/`)
is still used by the infrastructure layer and cannot be removed yet. The new Pydantic-based
protocol layer coexists alongside it.

**Completed:**
- [x] Add deprecation notices to `fints/types.py`
- [x] Add deprecation notices to `fints/fields.py`
- [x] Add deprecation notices to `fints/formals.py`
- [x] Add deprecation notices to `fints/parser.py`
- [x] Verify all 407 unit tests pass
- [x] Verify all 15 integration tests pass

**Future Work (not blocking):**
The following can be done incrementally as the infrastructure is migrated:
- [ ] Migrate infrastructure to use Pydantic segments
- [ ] Remove legacy `fints/types.py`
- [ ] Remove legacy `fints/fields.py`
- [ ] Rewrite `fints/formals.py` to re-export from `fints/protocol/formals/`
- [ ] Rewrite `fints/segments/*.py` to re-export from `fints/protocol/segments/`

---

## DRY Strategies

### 1. Annotated Types (Define Once, Use Everywhere)

```python
# Instead of repeating validation logic:
# ❌ Bad: Repeating in every model
class Model1(BaseModel):
    @field_validator('date', mode='before')
    def parse_date(cls, v):
        # Same logic repeated...

class Model2(BaseModel):
    @field_validator('date', mode='before')
    def parse_date(cls, v):
        # Same logic repeated...

# ✅ Good: Define once as Annotated type
FinTSDate = Annotated[date, BeforeValidator(parse_fints_date)]

class Model1(BaseModel):
    date: FinTSDate  # Validation included

class Model2(BaseModel):
    date: FinTSDate  # Same validation, no repetition
```

### 2. Base Classes for Segments

```python
# Instead of repeating common fields:
# ❌ Bad: Every segment repeats header
class HISAL5(FinTSSegment):
    header: SegmentHeader
    # ...

class HISAL6(FinTSSegment):
    header: SegmentHeader
    # ...

# ✅ Good: Base class handles common fields
class FinTSSegment(FinTSModel):
    header: SegmentHeader  # Defined once

class HISAL5(FinTSSegment):
    # header inherited
    ...
```

### 3. Version Inheritance

```python
# ❌ Bad: Duplicating all fields across versions
class HISAL5(FinTSSegment):
    account: Account
    currency: str
    balance_booked: Balance
    # 10 more fields...

class HISAL6(FinTSSegment):
    account: Account
    currency: str
    balance_booked: Balance
    # Same 10 fields...
    # + 2 new fields

# ✅ Good: Inherit common fields
class HISALBase(FinTSSegment):
    account_product: str
    currency: str
    balance_booked: Balance
    balance_pending: Balance | None = None

class HISAL5(HISALBase):
    SEGMENT_VERSION = 5
    account: AccountV2  # Version-specific

class HISAL6(HISALBase):
    SEGMENT_VERSION = 6
    account: AccountV3
    overdraft: Amount | None = None  # New in v6
```

### 4. Factory Functions for Parsing

```python
# ✅ Single entry point, handles all versions
def parse_hisal(data: list, version: int) -> HISALBase:
    """Parse any HISAL version."""
    segment_class = HISAL_VERSIONS.get(version)
    if not segment_class:
        raise ValueError(f"Unknown HISAL version: {version}")
    return segment_class.from_wire_list(data)
```

---

## Testing Strategy

### Unit Tests for Types
```python
# tests/unit/protocol/test_types.py
import pytest
from fints.protocol.types import FinTSDate, FinTSAmount, FinTSBool

class TestFinTSDate:
    def test_parse_string(self):
        # Create a model using the type
        from pydantic import BaseModel
        class M(BaseModel):
            d: FinTSDate

        m = M(d="20231225")
        assert m.d == date(2023, 12, 25)

    def test_parse_date_passthrough(self):
        class M(BaseModel):
            d: FinTSDate

        m = M(d=date(2023, 12, 25))
        assert m.d == date(2023, 12, 25)

    def test_serialize(self):
        class M(BaseModel):
            d: FinTSDate

        m = M(d=date(2023, 12, 25))
        assert m.model_dump()['d'] == "20231225"
```

### Integration Tests
```python
# tests/integration/test_pydantic_segments.py
def test_hisal6_parsing():
    """Test parsing real HISAL6 response."""
    raw_segment = [...]  # From recorded bank response

    segment = HISAL6.from_wire_list(raw_segment)

    assert segment.SEGMENT_TYPE == "HISAL"
    assert segment.SEGMENT_VERSION == 6
    assert isinstance(segment.balance_booked.amount.amount, Decimal)
```

### Backward Compatibility Tests
```python
def test_legacy_to_pydantic_conversion():
    """Ensure legacy models convert correctly."""
    from fints import formals

    legacy = formals.BankIdentifier(
        country_identifier="280",
        bank_code="12345678",
    )

    pydantic = BankIdentifier.from_legacy(legacy)

    assert pydantic.country_identifier == "280"
    assert pydantic.bank_code == "12345678"

    # Round-trip
    back_to_legacy = pydantic.to_legacy()
    assert back_to_legacy.country_identifier == legacy.country_identifier
```

---

## File Structure After Migration

```
fints/
├── infrastructure/
│   └── fints/
│       └── protocol/                # Pydantic protocol layer
│           ├── __init__.py
│           ├── parameters.py        # Existing - BPD/UPD management
│           ├── types.py             # NEW - Annotated types
│           ├── base.py              # NEW - Base models
│           ├── formals/             # FUTURE - Pydantic DEGs
│           │   ├── __init__.py
│           │   ├── identifiers.py
│           │   ├── amounts.py
│           │   └── security.py
│           └── segments/            # FUTURE - Pydantic segments
│               ├── __init__.py
│               ├── saldo.py
│               ├── statement.py
│               └── ...
│
├── types.py                     # DEPRECATED → delete after migration
├── fields.py                    # DEPRECATED → delete after migration
├── formals.py                   # DEPRECATED → re-exports from protocol/formals
├── segments/                    # DEPRECATED → re-exports from protocol/segments
│
├── domain/                      # Unchanged
├── application/                 # Unchanged
└── clients/                     # Unchanged
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Code reduction | -30% lines in protocol layer |
| Type coverage | 100% type hints |
| Test coverage | ≥90% on new code |
| Performance | ≤10% slower than legacy |
| API compatibility | Zero breaking changes during migration |

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Performance regression | Benchmark early, optimize hot paths |
| Parser incompatibility | Extensive testing with real bank responses |
| Breaking changes | Feature flags, gradual rollout |
| Incomplete migration | Clear phase boundaries, rollback plan |
| Developer confusion | Clear documentation, migration guide |

---

## Migration Complete Summary

### Final Structure

```
fints/infrastructure/fints/protocol/
├── __init__.py              # Main exports (190+ symbols)
├── parameters.py            # BPD/UPD parameter stores
├── base.py                  # FinTSModel, FinTSSegment, SegmentSequence
├── types.py                 # 13 Annotated types (FinTSDate, FinTSAmount, etc.)
├── parser.py                # FinTSParser, FinTSSerializer, SegmentRegistry
├── formals/
│   ├── __init__.py          # Exports all DEGs and enums
│   ├── enums.py             # 30+ enums (SecurityMethod, CreditDebit, etc.)
│   ├── identifiers.py       # BankIdentifier, AccountIdentifier, etc.
│   ├── amounts.py           # Amount, Balance, BalanceSimple, Timestamp
│   ├── security.py          # SecurityProfile, KeyName, Certificate, etc.
│   └── responses.py         # Response, ReferenceMessage
└── segments/
    ├── __init__.py          # Exports all 34 segment classes
    ├── saldo.py             # HKSAL5-7, HISAL5-7 (balance)
    ├── accounts.py          # HKSPA1, HISPA1 (SEPA accounts)
    ├── transactions.py      # HKKAZ5-7, HIKAZ5-7, HKCAZ1, HICAZ1
    └── statements.py        # HKEKA3-5, HIEKA3-5, HKKAU1-2, HIKAU1-2
```

### Test Coverage

| Phase | Description | Tests Added | Cumulative |
|-------|-------------|-------------|------------|
| 1 | Types & Base | 101 | 303 |
| 2 | Core DEGs | 44 | 347 |
| 3 | Balance/Account Segments | 16 | 363 |
| 4 | Transaction/Statement Segments | 17 | 380 |
| 5 | Parser & Serializer | 27 | **407** |
| 6 | Cleanup & Integration | - | 407 + 15 integration |

### Usage Example

```python
from fints.infrastructure.fints.protocol import (
    # Parser
    FinTSParser,
    FinTSSerializer,
    SegmentRegistry,

    # Base models
    FinTSModel,
    FinTSSegment,
    SegmentSequence,

    # Types
    FinTSDate,
    FinTSAmount,

    # Segments
    HISAL6,
    HKKAZ7,

    # DEGs
    BankIdentifier,
    AccountInternational,
    Amount,
    Balance,
)

# Parse a FinTS message
parser = FinTSParser()
segments = parser.parse_message(raw_bytes)

# Find balance segments
for seg in segments.find_segments("HISAL"):
    print(f"Account: {seg.account.iban}")
    print(f"Balance: {seg.balance_booked.signed_amount} {seg.currency}")

# Create a custom model
class MyModel(FinTSModel):
    date: FinTSDate
    amount: FinTSAmount

model = MyModel(date="20231225", amount="1234,56")
print(model.date)    # datetime.date(2023, 12, 25)
print(model.amount)  # Decimal('1234.56')
```

### Coexistence with Legacy Code

The new Pydantic-based protocol layer coexists with the legacy Container-based system:

| Component | Legacy Location | New Location | Status |
|-----------|-----------------|--------------|--------|
| Types | `fints/types.py` | `protocol/types.py` | Deprecated (docstring) |
| Fields | `fints/fields.py` | `protocol/base.py` | Deprecated (docstring) |
| Formals | `fints/formals.py` | `protocol/formals/` | Deprecated (docstring) |
| Segments | `fints/segments/` | `protocol/segments/` | Deprecated (docstring) |
| Parser | `fints/parser.py` | `protocol/parser.py` | Deprecated (docstring) |

The infrastructure layer (`fints/infrastructure/fints/`) still uses the legacy code.
Migration to Pydantic models can be done incrementally.

