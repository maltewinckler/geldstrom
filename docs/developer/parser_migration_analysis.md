# Parser Migration Analysis: Legacy vs Pydantic

## Executive Summary

The legacy parser and Pydantic parser have fundamentally different approaches to handling nested Data Element Groups (DEGs). The legacy parser uses **type-aware field iteration** while the Pydantic parser uses **positional mapping**. This difference causes failures when parsing complex nested structures.

---

## Wire Format Background

FinTS uses three separators:
- `'` (apostrophe) - separates segments
- `+` (plus) - separates DEGs at the segment level
- `:` (colon) - separates Data Elements within a DEG

**Critical**: Nested DEGs are FLATTENED in the wire format. All nested DEs are connected by colons.

### Example: KeyName DEG

`KeyName` contains a nested `BankIdentifier`:

```
KeyName
├── bank_identifier: BankIdentifier
│   ├── country_identifier
│   └── bank_code
├── user_id
├── key_type
├── key_number
└── key_version
```

Wire format flattens to:
```
280:12345678:4513830351:V:0:0
```

Where:
- `280` = country_identifier (from BankIdentifier)
- `12345678` = bank_code (from BankIdentifier)
- `4513830351` = user_id
- `V` = key_type
- `0` = key_number
- `0` = key_version

---

## Key Difference 1: Type Information at Parse Time

### Legacy Parser

```python
def parse_deg(self, clazz, data_i, required=True):
    retval = clazz()

    for name, field in retval._fields.items():
        constructed = isinstance(field, DataElementGroupField)

        if not constructed:
            # Simple field - take next value
            setattr(retval, name, next(data_i))
        else:
            # DEG field - RECURSE with the exact type
            deg = self.parse_deg(field.type, data_i, required)
            setattr(retval, name, deg)
```

**Key insight**: The legacy parser knows `field.type` for each DEG field and recursively parses it, consuming the correct number of data elements.

### Pydantic Parser

```python
def from_wire_list(cls, data: list) -> T:
    kwargs = {}
    for i, value in enumerate(data):
        field_name = field_names[i]
        if isinstance(value, list) and _is_fints_model_type(annotation):
            # Already structured - parse nested
            value = model_type.from_wire_list(value)
        kwargs[field_name] = value
```

**Problem**: When data is flat (not nested lists), the parser takes ONE element per field, regardless of whether the field is a nested DEG.

### Result

For `KeyName` parsing:

| Data Index | Legacy Parser | Pydantic Parser |
|------------|---------------|-----------------|
| 0: '280' | → bank_identifier.country_identifier | → bank_identifier (WRONG!) |
| 1: '12345678' | → bank_identifier.bank_code | → user_id (WRONG!) |
| 2: '4513830351' | → user_id | → key_type (WRONG!) |
| 3: 'V' | → key_type | → key_number (WRONG!) |
| 4: '0' | → key_number | → key_version (WRONG!) |
| 5: '0' | → key_version | (ignored) |

---

## Key Difference 2: Repeated DEG Fields

### Example: HITANS6 Segment

```python
# Legacy definition
class ParameterTwostepTAN6(ParameterTwostepCommon):
    twostep_parameters = DataElementGroupField(
        type=TwoStepParameters6,
        min_count=1,
        max_count=98  # Can have up to 98 TAN methods!
    )
```

Each `TwoStepParameters6` has ~20 fields. Wire format:
```
HITANS:81:6+1+1+1+J:N:0:942:2:MTAN2:mobileTAN::mobile TAN:6:1:SMS:2048:J:1:N:0:2:N:J:00:0:N:1:944:2:SECUREGO:mobileTAN::SecureGo...
```

### Legacy Parser

```python
if field.count != 1:  # Repeated field
    i = 0
    while True:
        deg = self.parse_deg(field.type, data_i, required)
        getattr(retval, name)[i] = deg
        i += 1
        if field.max_count and i >= field.max_count:
            break
```

- Knows each `TwoStepParameters6` has 20 fields
- Parses them in groups of 20
- Stops when data exhausted or max_count reached

### Pydantic Parser

```python
if origin is list:
    while raw_index < len(raw_data):
        raw_value = raw_data[raw_index]
        raw_index += 1
        list_values.append(inner_type.from_wire_list([raw_value]))
```

- Doesn't know `TwoStepParameters6` needs 20 elements
- Wraps each single element in a list and tries to parse
- Fails because `from_wire_list(['942'])` can't create a full TwoStepParameters6

---

## Key Difference 3: Optional Field Handling

### Example: SecurityDateTime

```python
class SecurityDateTime(DataElementGroup):
    date_time_type = CodeField(...)        # required
    date = DataElementField(required=False) # optional
    time = DataElementField(required=False) # optional
```

Wire data might be: `['1']` (only date_time_type) or `['1', '20231225', '135432']`

### Legacy Parser

```python
for name, field in retval._fields.items():
    try:
        setattr(retval, name, next(data_i))
    except StopIteration:
        if field.required:
            raise
        break  # No more data, remaining optional fields stay default
```

- Handles `StopIteration` gracefully
- Optional fields get default values if data exhausted

### Pydantic Parser

- Uses fixed-position mapping
- If data is `['1']`, it assigns `'1'` to first field only
- This actually works for trailing optional fields
- BUT fails when optional fields are in the middle of the structure

---

## Root Cause Summary

| Issue | Legacy Parser | Pydantic Parser |
|-------|---------------|-----------------|
| Nested DEGs | Recursively parses using `field.type` | Doesn't know field count, takes 1 element |
| Repeated DEGs | Uses `field.count`/`max_count` to know group size | Doesn't know group size |
| Optional fields | Uses iterator exhaustion | Works for trailing, fails for middle |
| Type conversion | Field classes have `_parse_value()` | Uses Pydantic validators |

---

## Migration Plan

### Phase 1: Count Nested Fields Recursively

Add a function to count total wire elements for a Pydantic model:

```python
def _count_model_fields(model_type: type[FinTSModel]) -> int:
    """Count total wire elements consumed, including nested models."""
    count = 0
    for field_info in model_type.model_fields.values():
        nested_type = _extract_model_type(field_info.annotation)
        if nested_type:
            count += _count_model_fields(nested_type)
        else:
            count += 1
    return count
```

**Status**: ✅ Already implemented in `base.py`

### Phase 2: Fix `from_wire_list` for Flat Data

Update to consume correct number of elements:

```python
def from_wire_list(cls, data: list) -> T:
    data_index = 0
    kwargs = {}

    for field_name in field_names:
        if data_index >= len(data):
            break

        annotation = cls.model_fields[field_name].annotation

        if _is_fints_model_type(annotation):
            model_type = _extract_model_type(annotation)
            value = data[data_index]

            if isinstance(value, list):
                # Already structured
                parsed = model_type.from_wire_list(value)
                data_index += 1
            else:
                # Flat data - consume multiple elements
                nested_count = _count_model_fields(model_type)
                nested_data = data[data_index:data_index + nested_count]
                parsed = model_type.from_wire_list(nested_data)
                data_index += nested_count

            kwargs[field_name] = parsed
        else:
            kwargs[field_name] = data[data_index]
            data_index += 1

    return cls(**kwargs)
```

**Status**: ✅ Already implemented in `base.py`

### Phase 3: Fix `_parse_segment_as_class` for DEG Types

The parser's segment parsing also needs the same logic:

```python
def _parse_segment_as_class(self, cls, raw_segment, header):
    # For nested DEG types, use from_wire_list which handles flat data
    if _is_fints_model_type(annotation):
        model_type = _extract_model_type(annotation)
        if isinstance(raw_value, list):
            parsed_value = model_type.from_wire_list(raw_value)
            raw_index += 1
        else:
            # Flat - shouldn't happen at segment level
            # but handle defensively
            parsed_value = model_type.from_wire_list([raw_value])
            raw_index += 1
```

**Status**: ✅ Already implemented in `parser.py`

### Phase 4: Handle Repeated DEG Fields (NEW)

For fields like `twostep_parameters: list[TwoStepParameters6]`:

```python
if origin is list:
    inner_type = args[0]
    if hasattr(inner_type, "from_wire_list"):
        list_values = []
        deg_field_count = _count_model_fields(inner_type)

        while raw_index + deg_field_count <= len(raw_data):
            # Take exactly deg_field_count elements
            deg_data = raw_data[raw_index:raw_index + deg_field_count]
            list_values.append(inner_type.from_wire_list(deg_data))
            raw_index += deg_field_count

        data[field_name] = list_values
```

**Status**: ❌ NOT implemented - this is the missing piece!

### Phase 5: Complete Segment Definitions

Add all missing segment definitions:
- HIAZSS1 (Authorization Security Scheme)
- HIVISS1 (Visualization Information)
- Additional HITANS/HIPINS parameter versions

**Status**: ❌ Some segments not yet defined

### Phase 6: Validation Tolerance

Some bank responses have values outside expected formats. Options:
1. Add `mode='before'` validators that are lenient
2. Use `robust_mode` to catch ValidationError and return partial data
3. Define "loose" versions of types for parsing

**Status**: ⚠️ Uses robust_mode but some segments completely fail

---

## Implementation Priority

1. **HIGH**: Fix repeated DEG field parsing (Phase 4)
   - This is blocking HITANS/HIPINS parsing
   - Without TAN parameters, two-step authentication fails

2. **MEDIUM**: Add missing segment definitions (Phase 5)
   - HIAZSS, HIVISS are informational
   - Won't block core functionality

3. **LOW**: Validation tolerance (Phase 6)
   - Most segments work with current strict validation
   - Can be addressed case-by-case

---

## Testing Strategy

1. **Unit tests**: Parse real wire data for each segment type
2. **Roundtrip tests**: Parse → serialize → parse should give same result
3. **Integration tests**: Full bank communication with Pydantic parser

---

## Conclusion

The main blocker is **repeated DEG field parsing**. The parser currently doesn't know how to group flat elements into multiple DEG instances. Once this is fixed, response parsing should work.

The good news: The foundational work (`_count_model_fields`, flat data handling in `from_wire_list`) is already done. The remaining work is to apply this logic to list fields in `_parse_segment_as_class`.

