# FinTS 3.0 Protocol Reference

This document provides a comprehensive overview of the FinTS 3.0 (Financial Transaction Services) protocol as implemented in this library, including lessons learned from integration testing with multiple German banks.

## Table of Contents

1. [Overview](#overview)
2. [Message Structure](#message-structure)
3. [Dialog Flow](#dialog-flow)
4. [Segment Categories](#segment-categories)
5. [Security Mechanisms](#security-mechanisms)
6. [TAN Handling](#tan-handling)
7. [Bank-Specific Behaviors](#bank-specific-behaviors)
8. [Lessons Learned](#lessons-learned)

---

## Overview

FinTS 3.0 (formerly HBCI - Home Banking Computer Interface) is a German standard for online banking communication. It defines how banking software communicates with bank servers to perform operations like:

- Account information retrieval
- Balance queries
- Transaction history
- Payment initiation
- Statement downloads

### Key Concepts

| Term | Description |
|------|-------------|
| **Segment** | A logical unit of data in a FinTS message (like a function call) |
| **Dialog** | A session between client and bank, started with identification and ended explicitly |
| **BPD** | Bank Parameter Data - capabilities and configuration of the bank |
| **UPD** | User Parameter Data - accounts and permissions for the logged-in user |
| **TAN** | Transaction Authentication Number - second factor for authentication |

### Segment Naming Convention

FinTS segments follow a naming pattern:

| Prefix | Meaning | Direction |
|--------|---------|-----------|
| `HK` | Kundennachricht (Customer message) | Client → Bank |
| `HI` | Institutsnachricht (Institute message) | Bank → Client |
| `HN` | Nachrichtenkopf (Message header/envelope) | Both |

The suffix indicates the segment type:
- `S` suffix = Parameter segment (e.g., `HISPAS` = SEPA parameters)
- Number suffix = Version (e.g., `HKSAL7` = Balance query version 7)

---

## Message Structure

A FinTS message consists of:

```
HNHBK (Message Header)
├── HNVSK (Encryption Envelope Header)
│   └── HNVSD (Encrypted Data Container)
│       ├── HNSHK (Signature Header)
│       ├── [Business Segments...]
│       └── HNSHA (Signature Trailer)
└── HNHBS (Message Trailer)
```

### Envelope Segments

| Segment | Version | Purpose |
|---------|---------|---------|
| `HNHBK` | 3 | Message header - contains size, dialog ID, message number |
| `HNHBS` | 1 | Message trailer - confirms message number |
| `HNVSK` | 3 | Security envelope header - encryption parameters |
| `HNVSD` | 1 | Encrypted data container - wraps all content |
| `HNSHK` | 4 | Signature header - authentication info, security function |
| `HNSHA` | 2 | Signature trailer - PIN/TAN authentication |

### Security Parameters in HNVSK/HNSHK

```
HNVSK: security_profile = PIN:1 or PIN:2
       security_function = 998 (encryption identifier)

HNSHK: security_profile = PIN:1
       security_function = 999 (one-step) or 940/946/etc. (two-step TAN)
```

**Important**: The `security_method_version` differs between segments:
- `HNVSK` uses version `2` for two-step TAN mode
- `HNSHK` uses version `1` even for two-step TAN

---

## Dialog Flow

### Standard Dialog Sequence

```
1. Client → Bank: Dialog Initialization
   - HKIDN (Identification)
   - HKVVB (Processing Preparation)
   - [HKTAN] (if two-step TAN required)

2. Bank → Client: Dialog Response
   - HIRMG (Global status messages)
   - HIRMS (Segment status messages)
   - HIBPA (Bank Parameter Data)
   - HIUPA (User Parameter Data header)
   - HIUPD (User Parameter Data - accounts)
   - [HITAN] (TAN challenge if required)

3. Client → Bank: Business Operations
   - HKSPA (Get SEPA accounts)
   - HKSAL (Get balance)
   - HKCAZ (Get CAMT transactions)
   - etc.

4. Client → Bank: Dialog End
   - HKEND (End dialog)
```

### System ID Synchronization

For non-anonymous access, clients need a unique system ID:

```
1. Client → Bank: Sync Dialog
   - HKIDN (with system_id = "0")
   - HKVVB
   - HKSYN (synchronization request, mode = 0)

2. Bank → Client:
   - HISYN (contains new system_id)

3. Client → Bank: HKEND

4. Use obtained system_id for all subsequent dialogs
```

---

## Segment Categories

### Dialog Management Segments

| Segment | Description |
|---------|-------------|
| `HKIDN` | **Identification** - User ID, customer ID, system ID |
| `HKVVB` | **Processing Preparation** - BPD/UPD version, language, product info |
| `HKEND` | **End Dialog** - Closes the dialog session |
| `HKSYN` | **Synchronization** - Request system ID or signature ID |
| `HIRMG` | **Global Messages** - Status codes for entire message |
| `HIRMS` | **Segment Messages** - Status codes for specific segments |

### Bank/User Parameter Segments

| Segment | Description |
|---------|-------------|
| `HIBPA` | **Bank Parameter Data** - Bank capabilities, supported operations |
| `HIUPA` | **User Parameter Header** - UPD version |
| `HIUPD` | **User Parameter Data** - Account list with permissions |
| `HIKOM` | **Communication Access** - Server URLs and protocols |
| `HIPINS` | **PIN/TAN Info** - Which operations require TAN |
| `HITANS` | **TAN Mechanisms** - Available TAN methods and their parameters |

### Authentication Segments

| Segment | Description |
|---------|-------------|
| `HKTAN` | **TAN Submission** - Submit or request TAN |
| `HITAN` | **TAN Response** - Challenge, task reference, status |
| `HKTAB` | **TAN Media Query** - List available TAN media (devices) |
| `HITAB` | **TAN Media Response** - Available TAN media |

### Account Information Segments

| Segment | Description |
|---------|-------------|
| `HKSPA` | **SEPA Accounts Request** - Get SEPA-enabled accounts |
| `HISPA` | **SEPA Accounts Response** - IBAN, BIC, account details |
| `HKSAL` | **Balance Query** - Request account balance |
| `HISAL` | **Balance Response** - Booked balance, pending, available |

### Transaction History Segments

| Segment | Format | Description |
|---------|--------|-------------|
| `HKKAZ` | MT940 | **Account Transactions (MT940)** - Legacy SWIFT format |
| `HIKAZ` | MT940 | Response with MT940 statement data |
| `HKCAZ` | CAMT | **Account Transactions (CAMT)** - Modern XML format |
| `HICAZ` | CAMT | Response with CAMT XML data |
| `HKEKA` | PDF | **Electronic Statement** - Bank statements as documents |
| `HIEKA` | PDF | Response with statement list/content |

### Payment Segments

| Segment | Description |
|---------|-------------|
| `HKCCS` | **SEPA Credit Transfer** - Single payment |
| `HKCCM` | **SEPA Credit Transfer Batch** - Multiple payments |
| `HKDSE` | **SEPA Direct Debit** - Single debit |
| `HKDME` | **SEPA Direct Debit Batch** - Multiple debits |

### Depot/Securities Segments

| Segment | Description |
|---------|-------------|
| `HKWPD` | **Securities Holdings** - Request depot positions |
| `HIWPD` | **Securities Response** - Portfolio positions |

---

## Security Mechanisms

### PIN/TAN Authentication

FinTS uses PIN (Personal Identification Number) combined with TAN (Transaction Authentication Number) for authentication:

1. **One-Step Authentication** (`security_function = 999`)
   - PIN only, no TAN required
   - Used for: sync dialogs, read-only operations (bank-dependent)

2. **Two-Step Authentication** (`security_function = 940, 942, 946, etc.`)
   - PIN + TAN required
   - TAN method identified by security function code

### TAN Methods (Security Functions)

| Code | Method | Description |
|------|--------|-------------|
| `999` | One-Step | No TAN, PIN only |
| `920` | iTAN | Indexed TAN list (deprecated) |
| `921` | iTANplus | Enhanced iTAN (deprecated) |
| `940` | chipTAN | Hardware token with flicker code |
| `942` | pushTAN | App-based TAN delivery |
| `944` | chipTAN QR | Hardware token with QR code |
| `946` | Decoupled | App approval without TAN entry |

### TAN Process Codes

Used in `HKTAN.tan_process` field:

| Code | Description |
|------|-------------|
| `1` | Single-step TAN with hash |
| `2` | TAN submission (response to challenge) |
| `3` | Multiple TAN steps |
| `4` | TAN for segment (sent with business operation) |
| `S` | Status query (for decoupled TAN polling) |

---

## TAN Handling

### Standard TAN Flow (tan_process = 4)

```
1. Client sends: HKSAL + HKTAN(tan_process='4', segment_type='HKSAL')
2. Bank responds: HIRMS(0030) + HITAN(challenge, task_reference)
3. User enters TAN
4. Client sends: HKTAN(tan_process='2', task_reference, TAN)
5. Bank responds: HIRMS(0020) + HISAL(balance)
```

### Decoupled TAN Flow (tan_process = 4 → S)

```
1. Client sends: HKIDN + HKVVB + HKTAN(tan_process='4', segment_type='HKIDN')
2. Bank responds: HIRMS(3955) + HITAN(task_reference)
   - Code 3955 = "Security release via other channel"
3. User approves in banking app
4. Client polls: HKTAN(tan_process='S', task_reference)
5. Bank responds: HIRMS(3956) = still waiting, or HIRMS(0900) = approved
6. Repeat step 4-5 until approved
```

### HIPINS - TAN Requirements per Operation

The bank's BPD contains `HIPINS` which lists which operations require TAN:

```
HIPINS1.parameter.transaction_tans_required = [
    {transaction: 'HKSPA', tan_required: False},
    {transaction: 'HKSAL', tan_required: False},
    {transaction: 'HKCAZ', tan_required: True},
    ...
]
```

**Important**: Always check HIPINS before injecting HKTAN to avoid unnecessary 2FA requests.

---

## Bank-Specific Behaviors

### DKB (Deutsche Kreditbank)

| Aspect | Behavior |
|--------|----------|
| **Bank Code** | 12030000 |
| **Server** | https://fints.dkb.de/fints |
| **TAN Methods** | 940 (chipTAN), Decoupled (App) |
| **Sync Dialog Auth** | Must use one-step (999), rejects two-step |
| **Main Dialog Auth** | Requires decoupled TAN approval in app |
| **HKSPA** | Returns empty HISPA, accounts in HIUPD only |
| **HKSAL/HKSPA** | Requires HKTAN injection (per HIPINS) |
| **HIUPD Format** | `account_information` field is null, only IBAN provided |

**DKB-Specific Flow:**
```
1. Sync dialog with security_function=999 → Get system_id
2. Main dialog with security_function=940 + HKTAN
3. Bank returns 3955 (decoupled TAN required)
4. Poll with HKTAN(tan_process='S') until 0900 (approved)
5. Proceed with business operations (each may need HKTAN per HIPINS)
```

### Triodos Bank

| Aspect | Behavior |
|--------|----------|
| **Bank Code** | 50031000 |
| **Server** | https://fints-server.triodos.de/fints |
| **TAN Methods** | 946 (Decoupled/SecureGo) |
| **Sync Dialog Auth** | Accepts two-step |
| **Main Dialog Auth** | Immediate TAN delivery (no polling needed) |
| **HKSPA** | Returns full HISPA with accounts |
| **HKSAL/HKSPA** | Does NOT require HKTAN (per HIPINS) |
| **HIUPD Format** | Full `account_information` with account numbers |

**Triodos-Specific Flow:**
```
1. Dialog init with security_function=946 + HKTAN
2. TAN delivered to SecureGo app immediately
3. User enters TAN from app
4. HKSPA/HKSAL work without additional HKTAN
```

---

## Response Codes

### Success Codes (0xxx)

| Code | Meaning |
|------|---------|
| `0010` | Message received |
| `0020` | Order executed |
| `0030` | Order received - TAN required |
| `0100` | Dialog ended |
| `0900` | TAN valid |

### Warning Codes (3xxx)

| Code | Meaning |
|------|---------|
| `3040` | Continuation point - more data available (pagination) |
| `3060` | Warnings present |
| `3076` | Strong authentication not required |
| `3920` | Allowed one/two-step methods for user |
| `3955` | Security release via other channel (decoupled TAN) |
| `3956` | Strong customer authentication still pending |

### Error Codes (9xxx)

| Code | Meaning |
|------|---------|
| `9010` | Processing error |
| `9040` | Authentication missing |
| `9050` | Partial errors present |
| `9075` | Strong customer authentication required |
| `9160` | Data element missing |
| `9210` | Order rejected |
| `9800` | Dialog aborted |
| `9910` | Invalid PIN |
| `9930` | PIN locked |
| `9942` | PIN change required |

---

## Lessons Learned

### 1. Bank Implementations Vary Significantly

Despite FinTS being a standard, banks implement it differently:

- **Account Data Location**: DKB only provides accounts in HIUPD, while Triodos provides them in HISPA
- **TAN Requirements**: DKB requires TAN for HKSPA/HKSAL, Triodos doesn't
- **Decoupled TAN**: DKB requires polling, Triodos delivers immediately
- **HIUPD Structure**: DKB sends minimal data (IBAN only), Triodos sends full account info

### 2. Always Check HIPINS Before HKTAN Injection

Blindly injecting HKTAN for all business segments causes 2FA spam on banks that don't require it. The proper approach:

```python
def _segment_requires_tan(self, segment_type: str) -> bool:
    hipins = self._parameters.bpd.find_segment_first(HIPINS1)
    if hipins:
        for req in hipins.parameter.transaction_tans_required:
            if req.transaction == segment_type:
                return req.tan_required
    return True  # Assume required if not specified
```

### 3. Sync Dialog Must Use One-Step Auth

Some banks (like DKB) reject two-step TAN during the sync dialog (system ID acquisition). Always use `security_function=999` for sync:

```python
# Sync dialog - always one-step
sync_auth = StandaloneAuthenticationMechanism(
    security_function="999"
)

# Main dialog - use configured TAN method
main_auth = StandaloneAuthenticationMechanism(
    security_function=credentials.tan_method or "999"
)
```

### 4. Decoupled TAN Requires Polling

For decoupled TAN (code 3955):
1. Send HKTAN with `tan_process='S'` and `task_reference` from HITAN
2. Set `further_tan_follows=False`
3. Poll until response is NOT 3956 (still waiting)
4. Success on 0900 or any non-error response

### 5. Handle Null Fields Gracefully

Bank responses may have null/missing fields that are "required" per spec:
- DKB's HIUPD has `account_information=None`
- Some balances have missing `credit_debit` indicators

Always use `getattr(obj, 'field', default)` for optional fields.

### 6. UPD Fallback for Accounts

If HISPA returns no accounts, check UPD:

```python
accounts = hispa_response.accounts
if not accounts:
    accounts = upd.get_accounts()  # Fallback to HIUPD
```

### 7. Connection Management

- Create fresh `HTTPSDialogConnection` for each dialog
- Close sync dialog completely before opening main dialog
- Some banks use session cookies (like DKB's AWS load balancer)

### 8. Security Method Versions Matter

```python
# HNVSK (encryption envelope)
security_method_version = 2  # For two-step TAN

# HNSHK (signature header)
security_method_version = 1  # Always 1, even for two-step
```

---

## Appendix: Segment Quick Reference

### Most Common Segments

| Segment | Purpose | TAN Usually Required |
|---------|---------|---------------------|
| `HKIDN` | Identification | No (part of dialog init) |
| `HKVVB` | Process preparation | No (part of dialog init) |
| `HKSYN` | System ID sync | No |
| `HKSPA` | SEPA accounts | Bank-dependent |
| `HKSAL` | Balance query | Bank-dependent |
| `HKKAZ` | MT940 transactions | Usually yes |
| `HKCAZ` | CAMT transactions | Usually yes |
| `HKEKA` | Statements | Usually yes |
| `HKCCS` | SEPA transfer | Always yes |
| `HKTAN` | TAN handling | N/A |
| `HKEND` | End dialog | No |

### Version Support

| Operation | Versions | Recommended |
|-----------|----------|-------------|
| Balance (HKSAL) | 5, 6, 7 | 7 (uses KTI1/IBAN) |
| MT940 (HKKAZ) | 5, 6, 7 | 7 |
| CAMT (HKCAZ) | 1 | 1 |
| SEPA Accounts (HKSPA) | 1 | 1 |
| TAN (HKTAN) | 2, 5, 6, 7 | 7 |
| Statements (HKEKA) | 3, 4, 5 | 5 |

---

*Document created: November 28, 2025*
*Based on integration testing with DKB and Triodos banks*

