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

# Parameter management
from .parameters import (
    BankParameters,
    ParameterStore,
    UserParameters,
)

# Base models
from .base import (
    FinTSDataElementGroup,
    FinTSModel,
    FinTSSegment,
    SegmentHeader,
    SegmentSequence,
)

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

# Parser
from .parser import (
    FinTSParser,
    FinTSParserError,
    FinTSParserWarning,
    FinTSSerializer,
    SegmentRegistry,
    get_default_registry,
)

# Formals (DEGs, enums, constants)
from .formals import (
    # Base enum classes
    FinTSEnum,
    FinTSIntEnum,
    # Constants
    CUSTOMER_ID_ANONYMOUS,
    # Enums - Security
    SecurityMethod,
    IdentifiedRole,
    DateTimeType,
    SecurityRole,
    SecurityApplicationArea,
    CompressionFunction,
    KeyType,
    # Enums - Encryption
    UsageEncryption,
    OperationMode,
    EncryptionAlgorithmCoded,
    AlgorithmParameterName,
    AlgorithmParameterIVName,
    # Enums - Balance/Amount
    CreditDebit,
    # Enums - System
    SynchronizationMode,
    SystemIDStatus,
    UPDUsage,
    Language,
    ServiceType,
    # Enums - TAN
    TANMediaType,
    TANMediaClass,
    TANMediumStatus,
    TANTimeDialogAssociation,
    AllowedFormat,
    TANUsageOption,
    # Enums - Versioned aliases
    Language2,
    TANMediaType2,
    TANMediaClass3,
    TANMediaClass4,
    # Enums - Statement
    StatementFormat,
    Confirmation,
    # Identifiers
    BankIdentifier,
    AccountIdentifier,
    AccountInternational,
    AccountInternationalSEPA,
    COUNTRY_ALPHA_TO_NUMERIC,
    COUNTRY_NUMERIC_TO_ALPHA,
    # Amounts
    Amount,
    Balance,
    BalanceSimple,
    Timestamp,
    # Security
    SecurityProfile,
    SecurityIdentificationDetails,
    SecurityDateTime,
    EncryptionAlgorithm,
    HashAlgorithm,
    SignatureAlgorithm,
    KeyName,
    Certificate,
    UserDefinedSignature,
    # Responses
    Response,
    ReferenceMessage,
    # TAN
    TANMediaBase,
    TANMedia4,
    TANMedia5,
    ChallengeValidUntil,
    ParameterChallengeClass,
    ResponseHHDUC,
    TwoStepTANSubmission,
    # Transactions
    SupportedMessageTypes,
    BookedCamtStatements,
    SupportedSEPAPainMessages,
    BatchTransferParameter,
    ScheduledDebitParameter1,
    ScheduledDebitParameter2,
    ScheduledBatchDebitParameter1,
    ScheduledBatchDebitParameter2,
    QueryScheduledDebitParameter1,
    QueryScheduledDebitParameter2,
    # Parameters
    SupportedLanguages,
    SupportedHBCIVersions,
    CommunicationParameter,
    CommunicationAccess,
    AccountLimit,
    AllowedTransaction,
    AccountInformation,
    GetSEPAAccountParameter,
)

# Segments - All
from .segments import (
    # Dialog - Message header/trailer
    HNHBK3, HNHBS1, HNHBK_VERSIONS, HNHBS_VERSIONS,
    # Dialog - Responses
    HIRMG2, HIRMS2, HIRMG_VERSIONS, HIRMS_VERSIONS,
    # Dialog - Synchronization
    HKSYN3, HISYN4, HKSYN_VERSIONS, HISYN_VERSIONS,
    # Dialog - End
    HKEND1, HKEND_VERSIONS,
    # Message - Encryption
    HNVSK3, HNVSD1, HNVSK_VERSIONS, HNVSD_VERSIONS,
    # Message - Signature
    HNSHK4, HNSHA2, HNSHK_VERSIONS, HNSHA_VERSIONS,
    # Auth - Identification
    HKIDN2, HKIDN_VERSIONS,
    # Auth - Processing
    HKVVB3, HKVVB_VERSIONS,
    # Auth - TAN Request
    HKTANBase, HKTAN2, HKTAN6, HKTAN7, HKTAN_VERSIONS,
    # Auth - TAN Response
    HITANBase, HITAN6, HITAN7, HITAN_VERSIONS,
    # Auth - TAN Media
    HKTAB4, HKTAB5, HITAB4, HITAB5, HKTAB_VERSIONS, HITAB_VERSIONS,
    # Bank - BPD
    HIBPA3, HIBPA_VERSIONS,
    # Bank - UPD
    HIUPA4, HIUPD6, HIUPA_VERSIONS, HIUPD_VERSIONS,
    # Bank - Communication
    HKKOM4, HIKOM4, HKKOM_VERSIONS, HIKOM_VERSIONS,
    # PIN/TAN
    TransactionTANRequired, ParameterPinTan,
    TwoStepParameters6, TwoStepParameters7,
    ParameterTwostepTAN6, ParameterTwostepTAN7,
    ParameterSegmentBase,
    HIPINS1, HITANS6, HITANS7,
    HIPINS_VERSIONS, HITANS_VERSIONS,
)

# Segments - Business operations
from .segments import (
    # Balance segments
    HKSAL5,
    HKSAL6,
    HKSAL7,
    HKSAL_VERSIONS,
    HISAL5,
    HISAL6,
    HISAL7,
    HISAL_VERSIONS,
    # Account segments
    HKSPA1,
    HISPA1,
    # Transaction segments
    HKKAZ5,
    HKKAZ6,
    HKKAZ7,
    HKKAZ_VERSIONS,
    HIKAZ5,
    HIKAZ6,
    HIKAZ7,
    HIKAZ_VERSIONS,
    HKCAZ1,
    HKCAZ_VERSIONS,
    HICAZ1,
    HICAZ_VERSIONS,
    # Statement segments
    ReportPeriod,
    HKEKA3,
    HKEKA4,
    HKEKA5,
    HKEKA_VERSIONS,
    HIEKA3,
    HIEKA4,
    HIEKA5,
    HIEKA_VERSIONS,
    HKKAU1,
    HKKAU2,
    HKKAU_VERSIONS,
    HIKAU1,
    HIKAU2,
    HIKAU_VERSIONS,
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
    "FinTSParserWarning",
    "FinTSSerializer",
    "SegmentRegistry",
    "get_default_registry",
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
    "TwoStepTANSubmission",
    # Formals - Transactions
    "SupportedMessageTypes",
    "BookedCamtStatements",
    "SupportedSEPAPainMessages",
    "BatchTransferParameter",
    "ScheduledDebitParameter1",
    "ScheduledDebitParameter2",
    "ScheduledBatchDebitParameter1",
    "ScheduledBatchDebitParameter2",
    "QueryScheduledDebitParameter1",
    "QueryScheduledDebitParameter2",
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
    "HNHBK3", "HNHBS1", "HNHBK_VERSIONS", "HNHBS_VERSIONS",
    "HIRMG2", "HIRMS2", "HIRMG_VERSIONS", "HIRMS_VERSIONS",
    "HKSYN3", "HISYN4", "HKSYN_VERSIONS", "HISYN_VERSIONS",
    "HKEND1", "HKEND_VERSIONS",
    # Segments - Message Security
    "HNVSK3", "HNVSD1", "HNVSK_VERSIONS", "HNVSD_VERSIONS",
    "HNSHK4", "HNSHA2", "HNSHK_VERSIONS", "HNSHA_VERSIONS",
    # Segments - Auth
    "HKIDN2", "HKIDN_VERSIONS",
    "HKVVB3", "HKVVB_VERSIONS",
    "HKTANBase", "HKTAN2", "HKTAN6", "HKTAN7", "HKTAN_VERSIONS",
    "HITANBase", "HITAN6", "HITAN7", "HITAN_VERSIONS",
    "HKTAB4", "HKTAB5", "HITAB4", "HITAB5", "HKTAB_VERSIONS", "HITAB_VERSIONS",
    # Segments - Bank
    "HIBPA3", "HIBPA_VERSIONS",
    "HIUPA4", "HIUPD6", "HIUPA_VERSIONS", "HIUPD_VERSIONS",
    "HKKOM4", "HIKOM4", "HKKOM_VERSIONS", "HIKOM_VERSIONS",
    # Segments - PIN/TAN
    "TransactionTANRequired", "ParameterPinTan",
    "TwoStepParameters6", "TwoStepParameters7",
    "ParameterTwostepTAN6", "ParameterTwostepTAN7",
    "ParameterSegmentBase",
    "HIPINS1", "HITANS6", "HITANS7",
    "HIPINS_VERSIONS", "HITANS_VERSIONS",
    # Segments - Balance
    "HKSAL5", "HKSAL6", "HKSAL7", "HKSAL_VERSIONS",
    "HISAL5", "HISAL6", "HISAL7", "HISAL_VERSIONS",
    # Segments - Account
    "HKSPA1", "HISPA1",
    # Segments - Transaction
    "HKKAZ5", "HKKAZ6", "HKKAZ7", "HKKAZ_VERSIONS",
    "HIKAZ5", "HIKAZ6", "HIKAZ7", "HIKAZ_VERSIONS",
    "HKCAZ1", "HKCAZ_VERSIONS",
    "HICAZ1", "HICAZ_VERSIONS",
    # Segments - Statement
    "ReportPeriod",
    "HKEKA3", "HKEKA4", "HKEKA5", "HKEKA_VERSIONS",
    "HIEKA3", "HIEKA4", "HIEKA5", "HIEKA_VERSIONS",
    "HKKAU1", "HKKAU2", "HKKAU_VERSIONS",
    "HIKAU1", "HIKAU2", "HIKAU_VERSIONS",
]
