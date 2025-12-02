# FinTS Protocol Reference

This document provides a detailed technical description of the FinTS (Financial Transaction Services) protocol as implemented in geldstrom.

## Overview

FinTS (formerly HBCI - Home Banking Computer Interface) is a standardized protocol for online banking in Germany. It enables secure communication between banking software and financial institutions.

### Key Characteristics

- **Text-based wire format** with special delimiters
- **Segment-oriented** message structure
- **Strong security** via PIN/TAN authentication
- **Versioned segments** for backward compatibility
- **Stateful dialogs** with session management

### Protocol Versions

| Version | Name | Status |
|---------|------|--------|
| 2.2 | HBCI 2.2 | Legacy |
| 3.0 | FinTS 3.0 | Current |
| 4.0 | FinTS 4.0 | Proposed |

Geldstrom implements **FinTS 3.0** (protocol version 300).

## Wire Format

### Character Encoding

- **Default encoding**: ISO-8859-1 (Latin-1)
- **Binary data**: Prefixed with length marker

### Delimiters

FinTS uses three primary delimiters:

| Symbol | Name | Purpose |
|--------|------|---------|
| `'` | Apostrophe | Segment terminator |
| `+` | Plus | Data element separator |
| `:` | Colon | Data element group (DEG) separator |

### Escaping

Special characters within data are escaped with `?`:

| Sequence | Meaning |
|----------|---------|
| `?'` | Literal apostrophe |
| `?+` | Literal plus |
| `?:` | Literal colon |
| `??` | Literal question mark |
| `?@` | Literal at sign |

### Binary Data

Binary data is encoded with a length prefix:

```
@<length>@<binary_data>
```

Example: `@16@\x00\x01\x02...` (16 bytes of binary)

### Example Message

```
HNHBK:1:3+000000000123+300+dialogid123+1'
HNVSK:998:3+...encryption_header...'
HNVSD:999:1+@450@...encrypted_payload...'
HNHBS:2:1+1'
```

## Message Structure

### Hierarchy

```
Message
├── Header Segment (HNHBK)
├── Security Header (HNVSK) [optional]
├── Encrypted Data (HNVSD)
│   └── Decrypted Segments
│       ├── Signature Header (HNSHK)
│       ├── Business Segments (HKSAL, etc.)
│       └── Signature Trailer (HNSHA)
└── Trailer Segment (HNHBS)
```

### Segment Structure

Every segment follows this pattern:

```
<header>+<data_element_1>+<data_element_2>+...'
```

**Header format**: `<type>:<number>:<version>`

- **Type**: 5-6 character segment identifier (e.g., `HNHBK`, `HKSAL`)
- **Number**: Segment sequence number within message
- **Version**: Segment version number

Example:
```
HKSAL:3:7+DE89370400440532013000:COBADEFFXXX++EUR'
```

### Data Elements (DE)

Data elements are the atomic units of FinTS data:

| Type | Description | Example |
|------|-------------|---------|
| AN | Alphanumeric | `Mustermann` |
| NUM | Numeric | `12345` |
| BOOL | Boolean | `J` (yes) / `N` (no) |
| DATE | Date (YYYYMMDD) | `20231225` |
| TIME | Time (HHMMSS) | `143022` |
| BIN | Binary | `@16@...` |
| ID | Identifier | `0` or `dialogid123` |
| CODE | Coded value | `C` (credit) |

### Data Element Groups (DEG)

DEGs combine multiple related data elements, separated by colons:

```
<de1>:<de2>:<de3>
```

Example - Bank Identifier DEG:
```
280:12345678
 ^    ^
 |    └── Bank code (BLZ)
 └─────── Country code (280 = Germany)
```

Example - Account Identifier DEG:
```
DE89370400440532013000:COBADEFFXXX::280:37040044
│                       │             │    │
│                       │             │    └── Bank code
│                       │             └─────── Country code
│                       └───────────────────── BIC
└───────────────────────────────────────────── IBAN
```

## Segment Types

### Naming Convention

Segment types follow a naming pattern:

| Prefix | Meaning | Direction |
|--------|---------|-----------|
| `HK` | Kundennachricht (Customer) | Client → Bank |
| `HI` | Institutnachricht (Institute) | Bank → Client |
| `HN` | Nachricht (Message) | Both |

### Core Segments

#### Message Framing

| Segment | Version | Description |
|---------|---------|-------------|
| `HNHBK` | 3 | Message header (size, dialog ID, message number) |
| `HNHBS` | 1 | Message trailer (message number) |

#### Security

| Segment | Version | Description |
|---------|---------|-------------|
| `HNVSK` | 3 | Encryption header (algorithm, key info) |
| `HNVSD` | 1 | Encrypted data container |
| `HNSHK` | 4 | Signature header (authentication) |
| `HNSHA` | 2 | Signature trailer (PIN/TAN) |

#### Authentication

| Segment | Version | Description |
|---------|---------|-------------|
| `HKIDN` | 2 | Identification (user credentials) |
| `HKVVB` | 3 | Processing preparation |
| `HKSYN` | 3 | Synchronization request |
| `HISYN` | 4 | Synchronization response |
| `HKEND` | 1 | Dialog end |

#### Responses

| Segment | Version | Description |
|---------|---------|-------------|
| `HIRMG` | 2 | Global response messages |
| `HIRMS` | 2 | Segment-specific responses |

#### Bank Parameters

| Segment | Version | Description |
|---------|---------|-------------|
| `HIBPA` | 3 | Bank Parameter Data (BPD) |
| `HIKOM` | 4 | Communication parameters |
| `HIPINS` | 1 | PIN/TAN information |
| `HITANS` | 1-7 | Two-step TAN parameters |

#### User Parameters

| Segment | Version | Description |
|---------|---------|-------------|
| `HIUPA` | 4 | User Parameter Data header |
| `HIUPD` | 6 | Account information |

### Business Segments

#### Account Discovery

| Segment | Version | Description |
|---------|---------|-------------|
| `HKSPA` | 1-3 | SEPA account request |
| `HISPA` | 1-3 | SEPA account response |

#### Balance Queries

| Segment | Version | Description |
|---------|---------|-------------|
| `HKSAL` | 5-7 | Balance request |
| `HISAL` | 5-7 | Balance response |

#### Transaction History

| Segment | Version | Description |
|---------|---------|-------------|
| `HKKAZ` | 5-7 | Transaction request (MT940) |
| `HIKAZ` | 5-7 | Transaction response (MT940) |
| `HKCAZ` | 1 | Transaction request (CAMT) |
| `HICAZ` | 1 | Transaction response (CAMT) |

#### TAN Management

| Segment | Version | Description |
|---------|---------|-------------|
| `HKTAN` | 2-7 | TAN submission/request |
| `HITAN` | 2-7 | TAN response/challenge |
| `HKTAB` | 4-5 | TAN media request |
| `HITAB` | 4-5 | TAN media response |

## Security Model

### PIN/TAN Overview

German banks use PIN/TAN (Personal Identification Number / Transaction Authentication Number) for authentication:

```
┌──────────────────────────────────────────────────────────────┐
│                      Security Layers                          │
├──────────────────────────────────────────────────────────────┤
│  Transport: HTTPS/TLS 1.2+                                   │
├──────────────────────────────────────────────────────────────┤
│  Message: Two-key triple DES encryption                       │
├──────────────────────────────────────────────────────────────┤
│  Authentication: PIN + TAN                                    │
└──────────────────────────────────────────────────────────────┘
```

### Security Profile

The security profile defines the cryptographic methods:

```
PIN:1
 ^   ^
 |   └── Version
 └────── Method (PIN/TAN)
```

Supported methods:
- `PIN`: PIN/TAN security
- `RDH`: RSA-DES-Hybrid (key files)
- `DDV`: DES-DES-Verfahren (chip card)

### Encryption

Messages are encrypted using the HNVSK/HNVSD segment pair:

**HNVSK (Encryption Header)**:
- Security profile (PIN:1)
- Security function (998 = encryption)
- Security role (1 = ISS = issuer)
- Encryption algorithm (2-key triple DES)
- Key name (identifies the encryption key)

**HNVSD (Encrypted Data)**:
- Contains the encrypted segment payload
- Decrypted data contains nested segments

### Signature

Messages are signed using the HNSHK/HNSHA segment pair:

**HNSHK (Signature Header)**:
- Security profile
- Security function (TAN function code)
- Control reference (links to HNSHA)
- Security date/time
- Hash algorithm (SHA-256)
- Signature algorithm
- Key name

**HNSHA (Signature Trailer)**:
- Control reference (links to HNSHK)
- Validation result
- User-defined signature (contains PIN and optionally TAN)

### TAN Procedures

#### One-Step TAN (Deprecated)

Single message contains both request and TAN.

#### Two-Step TAN (Current)

Two-step process with challenge-response:

```
Step 1: Request
Client: HKSAL (balance request)
        HKTAN (process=4, empty TAN)
Bank:   HITAN (challenge, reference)

Step 2: Response
Client: HKTAN (process=2, TAN, reference)
Bank:   HISAL (balance result)
```

#### Decoupled TAN

App-based approval without entering TAN:

```
┌────────┐          ┌────────┐          ┌─────────┐
│ Client │          │  Bank  │          │   App   │
└───┬────┘          └───┬────┘          └────┬────┘
    │                   │                    │
    │ HKSAL + HKTAN     │                    │
    │──────────────────▶│                    │
    │                   │   Push Notify      │
    │ HITAN (pending)   │───────────────────▶│
    │◀──────────────────│                    │
    │                   │                    │
    │   Poll: HKTAN     │                    │
    │──────────────────▶│   User Approves    │
    │                   │◀───────────────────│
    │ HITAN (approved)  │                    │
    │◀──────────────────│                    │
    │                   │                    │
    │ HISAL (result)    │                    │
    │◀──────────────────│                    │
```

**TAN Process Codes**:
- `1`: One-step (deprecated)
- `2`: TAN submission (step 2)
- `4`: TAN request (step 1)
- `S`: Decoupled (app-based)

## Dialog Flow

### Dialog Lifecycle

A FinTS dialog represents a session with the bank:

```
┌─────────────────────────────────────────────────────────────┐
│                     Dialog Lifecycle                         │
├─────────────────────────────────────────────────────────────┤
│  1. Initialize  │  HKIDN + HKVVB → Dialog ID assigned       │
│  2. Sync (opt)  │  HKSYN → System ID assigned               │
│  3. Operations  │  HKSAL, HKKAZ, etc.                       │
│  4. End         │  HKEND → Dialog closed                    │
└─────────────────────────────────────────────────────────────┘
```

### Initialization

```
Message 1 (Client → Bank):
  HNHBK (dialog_id="0")
  HNVSK + HNVSD [
    HNSHK
    HKIDN (bank_id, user_id, customer_id, system_id)
    HKVVB (bpd_version, upd_version, language, product_name)
    HKTAN (process=4)
    HNSHA (PIN)
  ]
  HNHBS

Message 2 (Bank → Client):
  HNHBK (dialog_id="ABC123")  ← Dialog ID assigned
  HNVSK + HNVSD [
    HIRMG (global status)
    HIRMS (segment status)
    HIBPA (bank parameters)
    HIUPA + HIUPD (user parameters, accounts)
    HITANS (TAN procedures)
    HITAN (TAN challenge if required)
  ]
  HNHBS
```

### System ID Synchronization

First-time connections require system ID assignment:

```
Client: HKSYN (mode=0)  ← Request new system ID
Bank:   HISYN (system_id="XYZ789")  ← Assigned ID
```

The system ID must be stored and reused for subsequent connections.

### Business Operation

```
Message 3 (Client → Bank):
  HNHBK (dialog_id="ABC123", msg_num=2)
  HNVSK + HNVSD [
    HNSHK
    HKSAL (account, all_accounts=false)
    HKTAN (process=4)
    HNSHA (PIN)
  ]
  HNHBS

Message 4 (Bank → Client):
  HNHBK (dialog_id="ABC123", msg_num=2)
  HNVSK + HNVSD [
    HIRMG
    HIRMS
    HISAL (balance data)
    HITAN (or status)
  ]
  HNHBS
```

### Dialog End

```
Message N (Client → Bank):
  HNHBK (dialog_id="ABC123", msg_num=N)
  HNVSK + HNVSD [
    HNSHK
    HKEND (dialog_id)
    HNSHA (PIN)
  ]
  HNHBS

Message N+1 (Bank → Client):
  HNHBK
  HNVSK + HNVSD [
    HIRMG (status=0010, "Dialog beendet")
  ]
  HNHBS
```

## Response Codes

### Code Structure

Response codes are 4-digit numbers:

| Range | Category |
|-------|----------|
| 0xxx | Success |
| 3xxx | Warning |
| 9xxx | Error |

### Common Response Codes

| Code | Message | Meaning |
|------|---------|---------|
| 0010 | Nachricht entgegengenommen | Message received successfully |
| 0020 | Auftrag ausgeführt | Order executed |
| 0030 | Auftrag nicht ausgeführt | Order not executed (info only) |
| 0100 | Dialog beendet | Dialog ended |
| 3040 | Es liegen weitere Daten vor | More data available (pagination) |
| 3920 | Zugelassene TAN-Verfahren | Allowed TAN procedures |
| 9000 | Nachricht nicht erwartet | Unexpected message |
| 9010 | Nachricht nicht zulässig | Message not allowed |
| 9050 | Teilweise fehlerhaft | Partially failed |
| 9800 | Dialog abgebrochen | Dialog aborted |
| 9930 | Benutzer gesperrt | User locked |
| 9931 | PIN falsch | Wrong PIN |
| 9942 | PIN ungültig | Invalid PIN |

### Reference Elements

Response codes include a reference element pointing to the source:

```
HIRMS:4:2+0010::5+3040::5:Weitere Einträge vorhanden'
          ^     ^  ^
          |     |  └── Reference to segment/DE
          |     └───── Code 3040 (more data)
          └─────────── Code 0010 (success)
```

## Pagination

Large result sets are paginated using touch-ahead markers:

### Request with Continuation

```
HKKAZ:3:7+DE89370400440532013000:COBADEFFXXX++20230101+20231231+++12345'
                                                                  ^
                                                                  └── Continuation ID
```

### Response with More Data

```
HIRMS:4:2+3040::5:Weitere Einträge+0010::5'
          ^
          └── Code 3040 indicates more data

HIKAZ:5:7+@2048@...transaction_data...'

# Bank provides continuation marker for next request
```

### Pagination Loop

```python
continuation_id = None
while True:
    response = send_request(account, continuation_id)
    process_transactions(response)

    if has_more_data(response):  # Code 3040
        continuation_id = extract_continuation(response)
    else:
        break
```

## Bank Parameter Data (BPD)

BPD describes the bank's capabilities and is retrieved during dialog initialization.

### BPD Structure

```
HIBPA:3:3+...+<version>+<bank_id>+<max_transactions>+<languages>+<hbci_versions>+<url>'
```

### BPD Segments

| Segment | Content |
|---------|---------|
| HIBPA | BPD header (version, limits) |
| HIKOM | Communication URLs |
| HIPINS | PIN/TAN configuration |
| HITANS | Supported TAN procedures |
| HIKAZS | Transaction parameters |
| HISALS | Balance parameters |
| etc. | Per-operation parameters |

### BPD Versioning

BPD has a version number that increments when parameters change:

```
Client: HKVVB (bpd_version=78)  ← Current known version
Bank:   HIBPA (version=79)      ← Newer version available
        + Full BPD data
```

If client's version matches, bank returns minimal response.

## User Parameter Data (UPD)

UPD describes the user's accounts and permissions.

### UPD Structure

```
HIUPA:4:4+<user_id>+<version>+<usage>'
HIUPD:6:6+<account_data>+<allowed_transactions>'
```

### Account Information

Each HIUPD segment contains:
- Account number and subaccount
- Bank identifier
- IBAN and BIC
- Account currency
- Account holder name
- Allowed operations (list of segment types)

Example:
```
HIUPD:5:6+1234567890:0:280:12345678+DE89370400440532013000+COBADEFFXXX+EUR+
Max Mustermann+Girokonto+1+HKSAL:HKKAZ:HKCAZ:HKSPA'
```

## Format Standards

### MT940 (Transaction Statements)

Legacy format for transaction data:

```
:20:STARTUMS
:25:12345678/1234567890
:28C:00001/001
:60F:C231215EUR1000,00
:61:2312151215CR100,00NTRFNONREF//
:86:000?00ÜBERWEISUNG?10?20Verwendungszweck?32Max Mustermann
:62F:C231215EUR1100,00
-
```

### CAMT.052/053 (ISO 20022)

Modern XML format for transactions:

```xml
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.052.001.08">
  <BkToCstmrAcctRpt>
    <Rpt>
      <Ntry>
        <Amt Ccy="EUR">100.00</Amt>
        <CdtDbtInd>CRDT</CdtDbtInd>
        <BookgDt><Dt>2023-12-15</Dt></BookgDt>
        <NtryDtls>
          <TxDtls>
            <RmtInf><Ustrd>Payment reference</Ustrd></RmtInf>
          </TxDtls>
        </NtryDtls>
      </Ntry>
    </Rpt>
  </BkToCstmrAcctRpt>
</Document>
```

## Implementation Details

### Segment Registration

Segments are auto-registered via `__init_subclass__`:

```python
class HKSAL7(FinTSSegment, segment_type="HKSAL", version=7):
    """Balance request segment."""
    account: AccountInternational
    all_accounts: bool = False

# Automatically registered in SEGMENT_REGISTRY
# Parser can now instantiate HKSAL7 from wire data
```

### Version Selection

When multiple versions exist, select the highest supported:

```python
def find_highest_supported_version(
    operation: str,
    parameters: ParameterStore,
    available_versions: dict[int, type],
) -> type:
    """Select highest version supported by both client and bank."""
    supported = parameters.get_supported_versions(operation)
    for version in sorted(available_versions.keys(), reverse=True):
        if version in supported:
            return available_versions[version]
    raise ValueError(f"No compatible version for {operation}")
```

### Parser Architecture

```
Raw Bytes
    │
    ▼
┌──────────────────┐
│    Tokenizer     │  Splits by delimiters ('+', ':', "'")
│   (ParserState)  │  Handles escaping and binary data
└──────────────────┘
    │
    ▼
┌──────────────────┐
│ Segment Exploder │  Groups tokens into segment lists
│                  │  Extracts header (type:num:ver)
└──────────────────┘
    │
    ▼
┌──────────────────┐
│ Segment Parser   │  Looks up segment class by type+version
│                  │  Calls from_wire_list() on class
└──────────────────┘
    │
    ▼
┌──────────────────┐
│  Pydantic Model  │  Validates and constructs segment
│                  │  Type coercion and constraints
└──────────────────┘
```

### Serialization

Segments serialize back to wire format:

```python
segment = HKSAL7(
    header=SegmentHeader(type="HKSAL", number=3, version=7),
    account=AccountInternational(iban="DE89...", bic="COBADEFF"),
    all_accounts=False,
)

wire = segment.to_wire_list()
# ['HKSAL:3:7', ['DE89...', 'COBADEFF', '', '', ''], 'N']

serialized = FinTSSerializer.serialize_segment(segment)
# b"HKSAL:3:7+DE89...:COBADEFF+N'"
```

## References

### Specifications

- [FinTS 3.0 Formals](https://www.hbci-zka.de/spec/3_0.htm) - Core protocol specification
- [FinTS 3.0 PIN/TAN](https://www.hbci-zka.de/spec/3_0.htm) - Security procedures
- [FinTS 3.0 Messages](https://www.hbci-zka.de/spec/3_0.htm) - Segment definitions

### Related Standards

- ISO 20022 (CAMT.052/053) - Transaction reporting
- SWIFT MT940/MT942 - Legacy statement format
- SEPA - Single Euro Payments Area

