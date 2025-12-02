"""FinTS Protocol Layer - Pydantic-based protocol models and parameter management.

This module provides:
1. Parameter management (BPD/UPD handling)
2. Pydantic-based protocol types and models

Key Components:
- types: Annotated types for FinTS data elements (FinTSDate, FinTSAmount, etc.)
- base: Base models (FinTSModel, FinTSSegment, SegmentSequence)
- parameters: BPD/UPD parameter stores

Example:
    from geldstrom.infrastructure.fints.protocol import (
        FinTSModel, FinTSDate, FinTSAmount,
        ParameterStore,
    )

    class MyModel(FinTSModel):
        date: FinTSDate
        amount: FinTSAmount

    # Parses FinTS wire format automatically
    model = MyModel(date="20231225", amount="1234,56")
"""

from __future__ import annotations

# Base models
from .base import (
    FinTSDataElementGroup,
    FinTSModel,
    FinTSSegment,
    SegmentHeader,
    SegmentSequence,
)

# Formals (DEGs, enums, constants)
from .formals import (
    COUNTRY_ALPHA_TO_NUMERIC,
    COUNTRY_NUMERIC_TO_ALPHA,
    # Constants
    CUSTOMER_ID_ANONYMOUS,
    AccountIdentifier,
    AccountInformation,
    AccountInternational,
    AccountInternationalSEPA,
    AccountLimit,
    AlgorithmParameterIVName,
    AlgorithmParameterName,
    AllowedFormat,
    AllowedTransaction,
    # Amounts
    Amount,
    Balance,
    BalanceSimple,
    # Identifiers
    BankIdentifier,
    BatchTransferParameter,
    BookedCamtStatements,
    Certificate,
    ChallengeValidUntil,
    CommunicationAccess,
    CommunicationParameter,
    CompressionFunction,
    Confirmation,
    # Enums - Balance/Amount
    CreditDebit,
    DateTimeType,
    EncryptionAlgorithm,
    EncryptionAlgorithmCoded,
    # Base enum classes
    FinTSEnum,
    FinTSIntEnum,
    GetSEPAAccountParameter,
    HashAlgorithm,
    IdentifiedRole,
    KeyName,
    KeyType,
    Language,
    # Enums - Versioned aliases
    Language2,
    OperationMode,
    ParameterChallengeClass,
    ReferenceMessage,
    # Responses
    Response,
    ResponseHHDUC,
    SecurityApplicationArea,
    SecurityDateTime,
    SecurityIdentificationDetails,
    # Enums - Security
    SecurityMethod,
    # Security
    SecurityProfile,
    SecurityRole,
    ServiceType,
    SignatureAlgorithm,
    # Enums - Statement
    StatementFormat,
    SupportedHBCIVersions,
    # Parameters
    SupportedLanguages,
    # Transactions
    SupportedMessageTypes,
    SupportedSEPAPainMessages,
    # Enums - System
    SynchronizationMode,
    SystemIDStatus,
    TANMedia4,
    TANMedia5,
    # TAN
    TANMediaBase,
    TANMediaClass,
    TANMediaClass3,
    TANMediaClass4,
    # Enums - TAN
    TANMediaType,
    TANMediaType2,
    TANMediumStatus,
    TANTimeDialogAssociation,
    TANUsageOption,
    Timestamp,
    UPDUsage,
    # Enums - Encryption
    UsageEncryption,
    UserDefinedSignature,
)

# Parameter management
from .parameters import (
    BankParameters,
    ParameterStore,
    UserParameters,
)

# Parser
from .parser import (
    FinTSParser,
    FinTSParserError,
    FinTSSerializer,
)


# Segment class lookup (use FinTSSegment.get_segment_class() directly)
def get_segment_class(segment_type: str, version: int):
    """Get segment class by type and version (convenience wrapper)."""
    return FinTSSegment.get_segment_class(segment_type, version)


# Segments - All
# Segments - Business operations
from .segments import (
    # Bank - BPD
    HIBPA3,
    HIBPA_VERSIONS,
    HICAZ1,
    HICAZ_VERSIONS,
    HIEKA3,
    HIEKA4,
    HIEKA5,
    HIEKA_VERSIONS,
    HIKAU1,
    HIKAU2,
    HIKAU_VERSIONS,
    HIKAZ5,
    HIKAZ6,
    HIKAZ7,
    HIKAZ_VERSIONS,
    HIKOM4,
    HIKOM_VERSIONS,
    HIPINS1,
    HIPINS_VERSIONS,
    # Dialog - Responses
    HIRMG2,
    HIRMG_VERSIONS,
    HIRMS2,
    HIRMS_VERSIONS,
    HISAL5,
    HISAL6,
    HISAL7,
    HISAL_VERSIONS,
    HISPA1,
    HISYN4,
    HISYN_VERSIONS,
    HITAB4,
    HITAB5,
    HITAB_VERSIONS,
    HITAN6,
    HITAN7,
    HITAN_VERSIONS,
    HITANS6,
    HITANS7,
    HITANS_VERSIONS,
    # Bank - UPD
    HIUPA4,
    HIUPA_VERSIONS,
    HIUPD6,
    HIUPD_VERSIONS,
    HKCAZ1,
    HKCAZ_VERSIONS,
    HKEKA3,
    HKEKA4,
    HKEKA5,
    HKEKA_VERSIONS,
    # Dialog - End
    HKEND1,
    HKEND_VERSIONS,
    # Auth - Identification
    HKIDN2,
    HKIDN_VERSIONS,
    HKKAU1,
    HKKAU2,
    HKKAU_VERSIONS,
    # Transaction segments
    HKKAZ5,
    HKKAZ6,
    HKKAZ7,
    HKKAZ_VERSIONS,
    # Bank - Communication
    HKKOM4,
    HKKOM_VERSIONS,
    # Balance segments
    HKSAL5,
    HKSAL6,
    HKSAL7,
    HKSAL_VERSIONS,
    # Account segments
    HKSPA1,
    # Dialog - Synchronization
    HKSYN3,
    HKSYN_VERSIONS,
    # Auth - TAN Media
    HKTAB4,
    HKTAB5,
    HKTAB_VERSIONS,
    HKTAN2,
    HKTAN6,
    HKTAN7,
    HKTAN_VERSIONS,
    # Auth - Processing
    HKVVB3,
    HKVVB_VERSIONS,
    # Dialog - Message header/trailer
    HNHBK3,
    HNHBK_VERSIONS,
    HNHBS1,
    HNHBS_VERSIONS,
    HNSHA2,
    HNSHA_VERSIONS,
    # Message - Signature
    HNSHK4,
    HNSHK_VERSIONS,
    HNVSD1,
    HNVSD_VERSIONS,
    # Message - Encryption
    HNVSK3,
    HNVSK_VERSIONS,
    # Auth - TAN Response
    HITANBase,
    # Auth - TAN Request
    HKTANBase,
    ParameterPinTan,
    ParameterSegmentBase,
    ParameterTwostepTAN6,
    ParameterTwostepTAN7,
    # Statement segments
    ReportPeriod,
    # PIN/TAN
    TransactionTANRequired,
    TwoStepParameters6,
    TwoStepParameters7,
)

# Tokenizer (low-level)
from .tokenizer import ParserState, Token

# Types
from .types import (
    FinTSAlphanumeric,
    FinTSAmount,
    FinTSBinary,
    FinTSBool,
    FinTSCode,
    FinTSCountry,
    FinTSCurrency,
    FinTSDate,
    FinTSDigits,
    FinTSID,
    FinTSNumeric,
    FinTSText,
    FinTSTime,
    # Validators (for custom usage)
    parse_fints_amount,
    parse_fints_binary,
    parse_fints_bool,
    parse_fints_code,
    parse_fints_date,
    parse_fints_digits,
    parse_fints_numeric,
    parse_fints_text,
    parse_fints_time,
    # Serializers (for custom usage)
    serialize_fints_amount,
    serialize_fints_bool,
    serialize_fints_date,
    serialize_fints_numeric,
    serialize_fints_time,
)

__all__ = [
    # Parameter management
    "BankParameters",
    "ParameterStore",
    "UserParameters",
    # Base models
    "FinTSModel",
    "FinTSDataElementGroup",
    "FinTSSegment",
    "SegmentHeader",
    "SegmentSequence",
    # Types
    "FinTSAlphanumeric",
    "FinTSAmount",
    "FinTSBinary",
    "FinTSBool",
    "FinTSCode",
    "FinTSCountry",
    "FinTSCurrency",
    "FinTSDate",
    "FinTSDigits",
    "FinTSID",
    "FinTSNumeric",
    "FinTSText",
    "FinTSTime",
    # Validators
    "parse_fints_amount",
    "parse_fints_binary",
    "parse_fints_bool",
    "parse_fints_code",
    "parse_fints_date",
    "parse_fints_digits",
    "parse_fints_numeric",
    "parse_fints_text",
    "parse_fints_time",
    # Serializers
    "serialize_fints_amount",
    "serialize_fints_bool",
    "serialize_fints_date",
    "serialize_fints_numeric",
    "serialize_fints_time",
    # Parser
    "FinTSParser",
    "FinTSParserError",
    "FinTSSerializer",
    # Tokenizer
    "ParserState",
    "Token",
    # Segment lookup
    "get_segment_class",
    # Formals - Base enum classes
    "FinTSEnum",
    "FinTSIntEnum",
    # Formals - Constants
    "CUSTOMER_ID_ANONYMOUS",
    # Formals - Enums
    "SecurityMethod",
    "IdentifiedRole",
    "DateTimeType",
    "SecurityRole",
    "SecurityApplicationArea",
    "CompressionFunction",
    "KeyType",
    "UsageEncryption",
    "OperationMode",
    "EncryptionAlgorithmCoded",
    "AlgorithmParameterName",
    "AlgorithmParameterIVName",
    "CreditDebit",
    "SynchronizationMode",
    "SystemIDStatus",
    "UPDUsage",
    "Language",
    "ServiceType",
    "TANMediaType",
    "TANMediaClass",
    "TANMediumStatus",
    "TANTimeDialogAssociation",
    "AllowedFormat",
    "TANUsageOption",
    "Language2",
    "TANMediaType2",
    "TANMediaClass3",
    "TANMediaClass4",
    "StatementFormat",
    "Confirmation",
    # Formals - Identifiers
    "BankIdentifier",
    "AccountIdentifier",
    "AccountInternational",
    "AccountInternationalSEPA",
    "COUNTRY_ALPHA_TO_NUMERIC",
    "COUNTRY_NUMERIC_TO_ALPHA",
    # Formals - Amounts
    "Amount",
    "Balance",
    "BalanceSimple",
    "Timestamp",
    # Formals - Security
    "SecurityProfile",
    "SecurityIdentificationDetails",
    "SecurityDateTime",
    "EncryptionAlgorithm",
    "HashAlgorithm",
    "SignatureAlgorithm",
    "KeyName",
    "Certificate",
    "UserDefinedSignature",
    # Formals - Responses
    "Response",
    "ReferenceMessage",
    # Formals - TAN
    "TANMediaBase",
    "TANMedia4",
    "TANMedia5",
    "ChallengeValidUntil",
    "ParameterChallengeClass",
    "ResponseHHDUC",
    # Formals - Transactions
    "SupportedMessageTypes",
    "BookedCamtStatements",
    "SupportedSEPAPainMessages",
    "BatchTransferParameter",
    # Formals - Parameters
    "SupportedLanguages",
    "SupportedHBCIVersions",
    "CommunicationParameter",
    "CommunicationAccess",
    "AccountLimit",
    "AllowedTransaction",
    "AccountInformation",
    "GetSEPAAccountParameter",
    # Segments - Dialog
    "HNHBK3",
    "HNHBS1",
    "HNHBK_VERSIONS",
    "HNHBS_VERSIONS",
    "HIRMG2",
    "HIRMS2",
    "HIRMG_VERSIONS",
    "HIRMS_VERSIONS",
    "HKSYN3",
    "HISYN4",
    "HKSYN_VERSIONS",
    "HISYN_VERSIONS",
    "HKEND1",
    "HKEND_VERSIONS",
    # Segments - Message Security
    "HNVSK3",
    "HNVSD1",
    "HNVSK_VERSIONS",
    "HNVSD_VERSIONS",
    "HNSHK4",
    "HNSHA2",
    "HNSHK_VERSIONS",
    "HNSHA_VERSIONS",
    # Segments - Auth
    "HKIDN2",
    "HKIDN_VERSIONS",
    "HKVVB3",
    "HKVVB_VERSIONS",
    "HKTANBase",
    "HKTAN2",
    "HKTAN6",
    "HKTAN7",
    "HKTAN_VERSIONS",
    "HITANBase",
    "HITAN6",
    "HITAN7",
    "HITAN_VERSIONS",
    "HKTAB4",
    "HKTAB5",
    "HITAB4",
    "HITAB5",
    "HKTAB_VERSIONS",
    "HITAB_VERSIONS",
    # Segments - Bank
    "HIBPA3",
    "HIBPA_VERSIONS",
    "HIUPA4",
    "HIUPD6",
    "HIUPA_VERSIONS",
    "HIUPD_VERSIONS",
    "HKKOM4",
    "HIKOM4",
    "HKKOM_VERSIONS",
    "HIKOM_VERSIONS",
    # Segments - PIN/TAN
    "TransactionTANRequired",
    "ParameterPinTan",
    "TwoStepParameters6",
    "TwoStepParameters7",
    "ParameterTwostepTAN6",
    "ParameterTwostepTAN7",
    "ParameterSegmentBase",
    "HIPINS1",
    "HITANS6",
    "HITANS7",
    "HIPINS_VERSIONS",
    "HITANS_VERSIONS",
    # Segments - Balance
    "HKSAL5",
    "HKSAL6",
    "HKSAL7",
    "HKSAL_VERSIONS",
    "HISAL5",
    "HISAL6",
    "HISAL7",
    "HISAL_VERSIONS",
    # Segments - Account
    "HKSPA1",
    "HISPA1",
    # Segments - Transaction
    "HKKAZ5",
    "HKKAZ6",
    "HKKAZ7",
    "HKKAZ_VERSIONS",
    "HIKAZ5",
    "HIKAZ6",
    "HIKAZ7",
    "HIKAZ_VERSIONS",
    "HKCAZ1",
    "HKCAZ_VERSIONS",
    "HICAZ1",
    "HICAZ_VERSIONS",
    # Segments - Statement
    "ReportPeriod",
    "HKEKA3",
    "HKEKA4",
    "HKEKA5",
    "HKEKA_VERSIONS",
    "HIEKA3",
    "HIEKA4",
    "HIEKA5",
    "HIEKA_VERSIONS",
    "HKKAU1",
    "HKKAU2",
    "HKKAU_VERSIONS",
    "HIKAU1",
    "HIKAU2",
    "HIKAU_VERSIONS",
]
