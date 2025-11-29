# Core Modules Analysis

## Overview

This document analyzes the top-level `fints/` modules to determine their role in the architecture and whether they need to be reorganized.

## Key Finding

These files are **NOT legacy leftovers** - they are **foundational protocol building blocks** that the entire infrastructure depends on. They implement the FinTS 3.0 wire protocol: message parsing, segment definitions, data types, and field encoding.

## Module Analysis

### 1. `fints/types.py` - Core Type System ✅ KEEP

**Purpose**: Defines foundational types for FinTS data structures.

**Key Classes**:
- `SegmentSequence` - Collection of parsed segments
- `Container` - Base class for all data structures
- `Field` / `TypedField` - Field definition base classes
- `ValueList` - Repeated field values

**Used By**:
- `fints/infrastructure/fints/protocol/parameters.py`
- `fints/infrastructure/fints/dialog/responses.py`
- `fints/infrastructure/fints/auth/challenge.py`
- All segment definitions

**Status**: Core type system. Cannot be removed.

---

### 2. `fints/fields.py` - Field Type Definitions ✅ KEEP

**Purpose**: Defines all FinTS field types (data elements).

**Key Classes**:
- `DataElementField`, `DataElementGroupField`
- `TextField`, `NumericField`, `BinaryField`
- `DateField`, `TimeField`, `AmountField`
- `CodeField`, `BooleanField`, `PasswordField`

**Used By**:
- All `fints/segments/*.py` files
- `fints/formals.py`

**Status**: Protocol encoding layer. Cannot be removed.

---

### 3. `fints/formals.py` - Formal Data Structures ✅ KEEP

**Purpose**: Defines FinTS formal data structures (DEGs - Data Element Groups).

**Key Classes**:
- `SegmentHeader` - Segment identification
- `BankIdentifier` - Bank routing (BLZ + country)
- `SecurityProfile`, `KeyName`, `SecurityIdentificationDetails`
- `TwoStepParameters1-7` - TAN method definitions
- `Balance1`, `Balance2`, `Amount1`
- All enums (`SecurityMethod`, `Language2`, `CreditDebit2`, etc.)

**Used By**:
- `fints/infrastructure/fints/adapters/` (all adapters)
- `fints/infrastructure/fints/auth/standalone_mechanisms.py`
- `fints/infrastructure/fints/operations/`
- `fints/infrastructure/fints/dialog/factory.py`

**Status**: Protocol data definitions. Cannot be removed.

---

### 4. `fints/message.py` - Message Construction ✅ KEEP

**Purpose**: Defines FinTS message containers.

**Key Classes**:
- `FinTSMessage` - Base message class
- `FinTSCustomerMessage` - Client → Bank messages
- `FinTSInstituteMessage` - Bank → Client messages
- `MessageDirection` enum

**Used By**:
- `fints/infrastructure/fints/dialog/transport.py`
- `fints/infrastructure/fints/dialog/factory.py`
- `fints/infrastructure/fints/dialog/responses.py`
- `fints/infrastructure/fints/dialog/connection.py`

**Status**: Core message model. Cannot be removed.

---

### 5. `fints/parser.py` - Message Parser ✅ KEEP

**Purpose**: FinTS message parsing and serialization.

**Key Classes**:
- `FinTS3Parser` - Parses bytes → SegmentSequence
- `FinTS3Serializer` - Serializes SegmentSequence → bytes
- `ParserState`, `Token` - Tokenizer internals

**Used By**:
- `fints/infrastructure/fints/protocol/parameters.py`
- Implicitly via `SegmentSequence(bytes_data)`

**Status**: Protocol parser. Cannot be removed.

---

### 6. `fints/segments/` - Segment Definitions ✅ KEEP

**Purpose**: Defines all FinTS segment types.

**Files**:
- `base.py` - `FinTS3Segment`, `ParameterSegment`
- `auth.py` - `HKTAN2-7`, `HITAN2-7`, `HITANS1-7`, `HIPINS1`
- `dialog.py` - `HKSYN3`, `HISYN4`, `HKEND1`, `HIRMG2`, `HIRMS2`
- `accounts.py` - `HKSPA1`, `HISPA1`
- `saldo.py` - `HKSAL5-7`, `HISAL5-7`
- `statement.py` - `HKKAZ5-7`, `HIKAZ5-7`, `HKCAZ1`, `HICAZ1`, `HKEKA3-5`
- `bank.py` - `HIBPA3`, `HIUPA4`, `HIUPD6`, `HIKOM4`
- `message.py` - `HNVSK3`, `HNVSD1`, `HNSHK4`, `HNSHA2`
- Others for transfers, debits, depot, journal

**Used By**: Everything - the infrastructure constructs and parses these.

**Status**: Protocol segment definitions. Cannot be removed.

---

### 7. `fints/exceptions.py` - Exception Hierarchy ✅ KEEP

**Purpose**: Defines all FinTS-specific exceptions.

**Key Classes**:
- `FinTSError` - Base exception
- `FinTSConnectionError` - Network/HTTP errors
- `FinTSDialogError`, `FinTSDialogStateError`, `FinTSDialogInitError`
- `FinTSUnsupportedOperation` - Operation not supported by bank
- `FinTSClientPINError`, `FinTSSCARequiredError`

**Used By**:
- `fints/infrastructure/fints/dialog/`
- `fints/infrastructure/fints/operations/`
- `fints/infrastructure/fints/adapters/`

**Status**: Error handling. Cannot be removed.

---

### 8. `fints/models.py` - Simple Data Models ✅ KEEP

**Purpose**: Simple namedtuples for data exchange.

**Key Classes**:
- `SEPAAccount` - IBAN, BIC, account number, subaccount, BLZ
- `Saldo` - Account, date, value, currency
- `Holding` - Securities position data

**Used By**:
- All operations modules
- All adapters

**Status**: Data transfer objects. Cannot be removed.

---

### 9. `fints/utils.py` - Utility Functions ✅ KEEP

**Purpose**: Shared utility functions.

**Key Functions/Classes**:
- `mt940_to_array()` - Parse MT940 bank statements
- `compress_datablob()` / `decompress_datablob()` - Session state compression
- `Password` - Secure string handling
- `LogConfiguration` - Logging control
- `MT535_Miniparser` - Securities holdings parser
- `decode_phototan_image()` - PhotoTAN decoding

**Used By**:
- `fints/infrastructure/fints/adapters/connection.py`
- `fints/infrastructure/fints/dialog/connection.py`
- `fints/infrastructure/fints/operations/transactions.py`
- `fints/infrastructure/fints/auth/challenge.py`

**Status**: Essential utilities. Cannot be removed.

---

### 10. `fints/constants.py` - Shared Constants ✅ KEEP

**Purpose**: Protocol constants.

**Contents**:
- `ING_BANK_IDENTIFIER` - ING-specific workaround
- `SYSTEM_ID_UNASSIGNED = '0'` - Unassigned system ID marker

**Used By**:
- `fints/infrastructure/fints/adapters/connection.py`
- `fints/infrastructure/fints/dialog/factory.py`
- `fints/infrastructure/fints/operations/system_id.py`

**Status**: Essential constants. Cannot be removed.

---

### 11. `fints/connection.py` - Legacy HTTP Connection ⚠️ CAN REMOVE

**Purpose**: Original HTTP connection class.

**Key Class**: `FinTSHTTPSConnection`

**Status**: **REPLACED** by `fints/infrastructure/fints/dialog/connection.py` which has `HTTPSDialogConnection`. The old one is no longer used.

**Action**: Can be safely deleted.

---

### 12. `fints/security.py` - Security Mechanisms ⚠️ CAN SIMPLIFY

**Purpose**: Original security mechanism implementations.

**Key Classes**:
- `EncryptionMechanism`, `AuthenticationMechanism` - Protocol interfaces
- `PinTanDummyEncryptionMechanism`
- `PinTanAuthenticationMechanism`, `PinTanOneStepAuthenticationMechanism`, `PinTanTwoStepAuthenticationMechanism`

**Status**: **PARTIALLY REPLACED** by `fints/infrastructure/fints/auth/standalone_mechanisms.py`.
The TYPE_CHECKING imports for protocol interfaces are still used, but the implementations are not.

**Action**: Keep only the protocol interfaces, move to `fints/infrastructure/fints/auth/`.

---

## Recommended Architecture

```
fints/
├── __init__.py            # Package exports
├── clients/               # Public client API (presentation layer)
│
├── protocol/              # ⬅️ NEW: Move core protocol files here
│   ├── __init__.py
│   ├── types.py           # Core types (Container, SegmentSequence, Field)
│   ├── fields.py          # Field type definitions
│   ├── formals.py         # Formal data structures (DEGs, enums)
│   ├── message.py         # Message classes
│   ├── parser.py          # Parser/serializer
│   ├── models.py          # SEPAAccount, Saldo, Holding
│   └── segments/          # All segment definitions
│       ├── __init__.py
│       ├── base.py
│       ├── auth.py
│       ├── bank.py
│       ├── dialog.py
│       └── ...
│
├── domain/                # Domain models (already good)
├── application/           # Application layer (already good)
│
└── infrastructure/
    └── fints/
        ├── adapters/      # Port implementations
        ├── dialog/        # Dialog management
        ├── operations/    # Business operations
        ├── protocol/      # BPD/UPD management (rename?)
        └── auth/          # Authentication
```

## Migration Plan

### Phase 1: Remove Truly Obsolete Files
- Delete `fints/connection.py` (replaced by `dialog/connection.py`)
- Move security protocols from `fints/security.py` to `fints/infrastructure/fints/auth/`

### Phase 2: Create `fints/protocol/` Package (Optional)
This is a larger refactoring that would:
1. Create `fints/protocol/` directory
2. Move `types.py`, `fields.py`, `formals.py`, `message.py`, `parser.py`, `models.py`
3. Move `fints/segments/` to `fints/protocol/segments/`
4. Update all imports across the codebase

**Recommendation**: This is a large refactoring with significant risk. The current structure works and these files are foundational. Consider doing this only if there's a strong architectural reason.

### Phase 3: Simplify Remaining Top-Level Files
- `fints/exceptions.py` - Keep at top level (used everywhere)
- `fints/constants.py` - Keep at top level or merge into appropriate module
- `fints/utils.py` - Keep at top level (general utilities)

---

## Summary

| File | Status | Action |
|------|--------|--------|
| `types.py` | Core | Keep |
| `fields.py` | Core | Keep |
| `formals.py` | Core | Keep |
| `message.py` | Core | Keep |
| `parser.py` | Core | Keep |
| `models.py` | Core | Keep |
| `segments/` | Core | Keep |
| `exceptions.py` | Core | Keep |
| `constants.py` | Core | Keep |
| `utils.py` | Core | Keep |
| `connection.py` | **Obsolete** | **Delete** |
| `security.py` | Partially obsolete | Simplify (keep protocols only) |

The "messy top-level" appearance is actually **intentional layering**:
- These files form the **FinTS Protocol Layer** - a reusable implementation of the FinTS wire protocol
- The `infrastructure/` layer builds on top of this protocol layer
- This separation is correct DDD: protocol parsing is infrastructure, but it's shared infrastructure

---

*Document created: November 29, 2025*

