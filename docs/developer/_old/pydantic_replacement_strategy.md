# Aggressive Pydantic Replacement Strategy

## Current Architecture (Descriptor-Based)

Currently, there are **two separate type systems**:

### 1. Domain Layer (Already Pydantic)
```python
# fints/domain/model/balances.py
class BalanceAmount(BaseModel, frozen=True):
    amount: Decimal
    currency: str

class BalanceSnapshot(BaseModel, frozen=True):
    account_id: str
    as_of: datetime
    booked: BalanceAmount
```

### 2. Protocol Layer (Descriptor-Based)
```python
# fints/formals.py
class Balance1(DataElementGroup):
    credit_debit = CodeField(enum=CreditDebit2, length=1)
    amount = DataElementField(type='wrt')
    currency = DataElementField(type='cur')
    date = DataElementField(type='dat')
    time = DataElementField(type='tim', required=False)

# fints/segments/saldo.py
class HISAL6(FinTS3Segment):
    account = DataElementGroupField(type=Account3)
    balance_booked = DataElementGroupField(type=Balance2)
    # ... 10+ more fields
```

### Current Data Flow
```
                    ┌──────────────────────┐
                    │   Wire Format (bytes)│
                    │  HISAL:6:4+...+C:123,│
                    └──────────┬───────────┘
                               │ FinTS3Parser
                               ▼
                    ┌──────────────────────┐
                    │  Descriptor Objects  │
                    │   HISAL6 Container   │
                    │  (Field descriptors) │
                    └──────────┬───────────┘
                               │ Adapter conversion
                               ▼
                    ┌──────────────────────┐
                    │   Pydantic Domain    │
                    │   BalanceSnapshot    │
                    └──────────────────────┘
```

**Problem**: We maintain TWO type systems and manually convert between them.

---

## The Pydantic Replacement Strategy

### Concept: Unified Type System

Replace the descriptor-based `Field`/`Container` system with Pydantic models that handle BOTH:
1. Domain modeling (type safety, validation)
2. Wire format parsing/rendering (via custom validators)

### Where Pydantic Would Be Used

| Layer | Current | With Pydantic |
|-------|---------|---------------|
| **Domain models** | Pydantic ✅ | Pydantic ✅ (unchanged) |
| **Protocol DEGs** | `DataElementGroup` + `Field` descriptors | Pydantic with wire validators |
| **Segments** | `FinTS3Segment` + `Field` descriptors | Pydantic with segment structure |
| **Parser output** | `Container` instances | Pydantic instances |

---

## Concrete Example: Balance

### Current: Two Separate Definitions

**Protocol layer** (`formals.py`):
```python
class Balance1(DataElementGroup):
    credit_debit = CodeField(enum=CreditDebit2, length=1)
    amount = DataElementField(type='wrt')       # German decimal format
    currency = DataElementField(type='cur')     # 3-char ISO code
    date = DataElementField(type='dat')         # YYYYMMDD format
    time = DataElementField(type='tim', required=False)  # HHMMSS format
```

**Domain layer** (`domain/model/balances.py`):
```python
class BalanceAmount(BaseModel, frozen=True):
    amount: Decimal
    currency: str
```

**Adapter conversion** (manual):
```python
def _balance_from_operations(self, result) -> BalanceSnapshot:
    booked = result.booked
    amount = booked.amount if booked.status == "C" else -booked.amount
    return BalanceSnapshot(
        account_id=account_id,
        as_of=datetime.combine(booked.date, time.min),
        booked=BalanceAmount(amount=amount, currency=booked.currency),
    )
```

### With Pydantic: Unified Definition

```python
from pydantic import BaseModel, field_validator, field_serializer
from typing import Literal
from datetime import date, time, datetime
from decimal import Decimal


class FinTSBalance(BaseModel):
    """Balance in FinTS format - handles both domain and wire concerns."""

    credit_debit: Literal['C', 'D']
    amount: Decimal
    currency: str
    date: date
    time: time | None = None

    # --- Wire Format Parsing (incoming) ---

    @field_validator('credit_debit', mode='before')
    @classmethod
    def parse_credit_debit(cls, v):
        """Parse FinTS credit/debit indicator."""
        if v in ('C', 'D'):
            return v
        # Could also handle German 'H' (Haben) / 'S' (Soll)
        raise ValueError(f"Invalid credit_debit: {v}")

    @field_validator('amount', mode='before')
    @classmethod
    def parse_amount(cls, v):
        """Parse FinTS amount format (German decimals: 123,45)."""
        if isinstance(v, Decimal):
            return v
        if isinstance(v, str):
            # FinTS uses comma as decimal separator
            return Decimal(v.replace(',', '.'))
        return Decimal(v)

    @field_validator('date', mode='before')
    @classmethod
    def parse_date(cls, v):
        """Parse FinTS date format (YYYYMMDD)."""
        if isinstance(v, date):
            return v
        if isinstance(v, str) and len(v) == 8:
            return date(int(v[:4]), int(v[4:6]), int(v[6:8]))
        return v

    @field_validator('time', mode='before')
    @classmethod
    def parse_time(cls, v):
        """Parse FinTS time format (HHMMSS)."""
        if v is None:
            return None
        if isinstance(v, time):
            return v
        if isinstance(v, str) and len(v) == 6:
            return time(int(v[:2]), int(v[2:4]), int(v[4:6]))
        return v

    # --- Wire Format Rendering (outgoing) ---

    @field_serializer('amount')
    def render_amount(self, v: Decimal) -> str:
        """Render to FinTS amount format."""
        return str(v).replace('.', ',')

    @field_serializer('date')
    def render_date(self, v: date) -> str:
        """Render to FinTS date format."""
        return v.strftime('%Y%m%d')

    @field_serializer('time')
    def render_time(self, v: time | None) -> str | None:
        """Render to FinTS time format."""
        if v is None:
            return None
        return v.strftime('%H%M%S')

    # --- Domain Helpers ---

    @property
    def signed_amount(self) -> Decimal:
        """Amount with sign based on credit/debit."""
        return self.amount if self.credit_debit == 'C' else -self.amount

    @property
    def as_of(self) -> datetime:
        """Combined date/time as datetime."""
        return datetime.combine(self.date, self.time or time.min)

    # --- Wire Format Export ---

    def to_wire_list(self) -> list[str | None]:
        """Export as FinTS DEG list for serialization."""
        return [
            self.credit_debit,
            self.render_amount(self.amount),
            self.currency,
            self.render_date(self.date),
            self.render_time(self.time),
        ]

    @classmethod
    def from_wire_list(cls, data: list) -> 'FinTSBalance':
        """Parse from FinTS DEG list."""
        return cls(
            credit_debit=data[0],
            amount=data[1],
            currency=data[2],
            date=data[3],
            time=data[4] if len(data) > 4 else None,
        )
```

### Usage

```python
# Parsing from wire format
raw_data = ['C', '1234,56', 'EUR', '20231225', '143022']
balance = FinTSBalance.from_wire_list(raw_data)

print(balance.amount)          # Decimal('1234.56')
print(balance.date)            # date(2023, 12, 25)
print(balance.signed_amount)   # Decimal('1234.56')

# Rendering to wire format
wire = balance.to_wire_list()
# ['C', '1234,56', 'EUR', '20231225', '143022']
```

---

## Full Segment Example

### Current Approach
```python
class HISAL6(FinTS3Segment):
    account = DataElementGroupField(type=Account3)
    account_product = DataElementField(type='an', max_length=30)
    currency = DataElementField(type='cur')
    balance_booked = DataElementGroupField(type=Balance2)
    balance_pending = DataElementGroupField(type=Balance2, required=False)
    line_of_credit = DataElementGroupField(type=Amount1, required=False)
    # ... more fields
```

### Pydantic Approach
```python
from pydantic import BaseModel, Field
from typing import Annotated

# Annotated types for constraints
FinTSCurrency = Annotated[str, Field(min_length=3, max_length=3)]
FinTSAlphanumeric = Annotated[str, Field(max_length=30)]


class FinTSAccount(BaseModel):
    """Account identifier (KTZ)."""
    account_number: str
    subaccount: str | None = None
    bank_code: str
    country: str = "280"  # Germany

    @classmethod
    def from_wire_list(cls, data: list) -> 'FinTSAccount':
        return cls(
            account_number=data[0],
            subaccount=data[1],
            bank_code=data[3] if len(data) > 3 else None,
            country=data[2] if len(data) > 2 else "280",
        )


class HISAL6Response(BaseModel):
    """Saldenrückmeldung (Balance Response), version 6."""

    account: FinTSAccount
    account_product: FinTSAlphanumeric
    currency: FinTSCurrency
    balance_booked: FinTSBalance
    balance_pending: FinTSBalance | None = None
    line_of_credit: Decimal | None = None
    available_amount: Decimal | None = None

    class Config:
        # Segment metadata
        segment_type = "HISAL"
        segment_version = 6

    @classmethod
    def from_parsed_segment(cls, segment_data: list) -> 'HISAL6Response':
        """Parse from FinTS segment data."""
        return cls(
            account=FinTSAccount.from_wire_list(segment_data[1]),
            account_product=segment_data[2],
            currency=segment_data[3],
            balance_booked=FinTSBalance.from_wire_list(segment_data[4]),
            balance_pending=FinTSBalance.from_wire_list(segment_data[5])
                if segment_data[5] else None,
            # ... etc
        )
```

---

## What Would Change?

### Files to Replace

| Current File | Pydantic Replacement |
|--------------|---------------------|
| `fints/types.py` | Remove `Container`, `Field`, `ValueList` |
| `fints/fields.py` | Remove all field classes |
| `fints/formals.py` | Pydantic models with validators |
| `fints/segments/*.py` | Pydantic segment models |
| `fints/parser.py` | Simplified parser → Pydantic `.from_wire_list()` |

### Files That Stay

| File | Why |
|------|-----|
| `fints/domain/` | Already Pydantic ✅ |
| `fints/infrastructure/fints/adapters/` | Simplified (less conversion) |
| `fints/infrastructure/fints/dialog/` | Unchanged (uses segment instances) |

---

## Architecture Comparison

### Current (Dual Type System)
```
┌─────────────────────┐     ┌─────────────────────┐
│  Domain (Pydantic)  │ ◄── │  Protocol (Field)   │
│  - BalanceSnapshot  │     │  - Balance1         │
│  - Account          │     │  - HISAL6           │
└─────────────────────┘     └─────────────────────┘
         ▲                            ▲
         │ Adapter converts           │ Parser creates
         │                            │
┌─────────────────────┐     ┌─────────────────────┐
│    Application      │     │    Wire Format      │
└─────────────────────┘     └─────────────────────┘
```

### With Pydantic (Unified)
```
┌─────────────────────────────────────┐
│      Pydantic Protocol Models       │
│  - FinTSBalance (wire + domain)     │
│  - HISAL6Response                   │
│  - Has .from_wire_list() methods    │
└─────────────────────┬───────────────┘
                      │
         Direct use   │   or   Simple mapping
         ▼            ▼
┌──────────────┐    ┌──────────────┐
│   Domain     │    │  Wire Format │
│  (optional)  │    │   (bytes)    │
└──────────────┘    └──────────────┘
```

---

## Pros and Cons

### Pros ✅

1. **Single Type System**: No more manual conversion between Container and Pydantic
2. **Type Safety**: Full IDE support, type hints everywhere
3. **Validation**: Pydantic's powerful validation out of the box
4. **Familiarity**: Pydantic is widely known in Python ecosystem
5. **JSON Serialization**: Free JSON export/import
6. **Immutability**: `frozen=True` for domain models
7. **Documentation**: Automatic schema generation

### Cons ❌

1. **Major Rewrite**: ~15+ files, hundreds of classes
2. **Breaking Changes**: Public API will change
3. **Performance**: Pydantic validation has overhead (though v2 is fast)
4. **Testing**: All existing tests need updates
5. **Parser Changes**: Need to modify `FinTS3Parser` output
6. **Segment Versioning**: Managing HISAL5 vs HISAL6 vs HISAL7 becomes verbose

---

## Migration Path

### Phase 1: Hybrid (Low Risk)
- Keep existing `Field`/`Container` system
- Add Pydantic `.from_container()` methods
- Gradually migrate adapters to use Pydantic directly

### Phase 2: Core DEGs (Medium Risk)
- Replace `formals.py` DEGs with Pydantic
- Update parser to output Pydantic models
- Keep segment structure

### Phase 3: Segments (High Risk)
- Replace `FinTS3Segment` with Pydantic base
- Full parser rewrite
- Complete migration

---

## Recommendation

### Don't Do Full Replacement Unless:
- You have comprehensive test coverage
- You're willing to accept breaking changes
- Performance is acceptable for your use case
- You have time for a significant refactor

### Better Alternative: Hybrid Approach
1. Keep `Field`/`Container` for wire format
2. Use existing Pydantic domain models
3. Improve adapters to do cleaner conversion
4. Add type hints to `Field` system
5. Consider Pydantic for NEW segments only

This gives you the benefits of Pydantic in the domain layer without the risk of rewriting the proven protocol layer.

---

## Example: Hybrid Approach

```python
# Protocol layer stays as-is
class HISAL6(FinTS3Segment):
    balance_booked = DataElementGroupField(type=Balance2)
    ...

# But add clean conversion
class FinTSBalanceAdapter:
    @staticmethod
    def to_domain(balance: Balance2) -> BalanceAmount:
        """Convert protocol Balance to domain BalanceAmount."""
        return BalanceAmount(
            amount=balance.amount.amount if balance.credit_debit.value == 'C'
                   else -balance.amount.amount,
            currency=balance.amount.currency,
        )

    @staticmethod
    def to_protocol(domain: BalanceAmount, credit_debit: str) -> Balance2:
        """Convert domain BalanceAmount to protocol Balance."""
        return Balance2(
            credit_debit=CreditDebit2(credit_debit),
            amount=Amount1(amount=abs(domain.amount), currency=domain.currency),
            date=date.today(),
        )
```

This hybrid approach is cleaner and safer than a full rewrite.

