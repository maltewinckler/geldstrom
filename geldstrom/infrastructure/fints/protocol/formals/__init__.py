"""FinTS Formal Data Element Groups (DEGs) - Pydantic models.

This module provides Pydantic-based implementations of FinTS DEGs,
replacing the legacy Container-based definitions in fints/formals.py.

Organization:
- enums: All FinTS enumeration types
- identifiers: Bank and account identifiers
- amounts: Amount and balance types
- security: Security-related DEGs
- responses: Response message types
- tan: TAN-related DEGs
- transactions: Transaction-related DEGs
- parameters: BPD/UPD-related DEGs
"""
from __future__ import annotations

# Constants
CUSTOMER_ID_ANONYMOUS = '9999999999'

from .enums import (
    # Base classes
    FinTSEnum,
    FinTSIntEnum,
    # Security
    SecurityMethod,
    IdentifiedRole,
    DateTimeType,
    SecurityRole,
    SecurityApplicationArea,
    CompressionFunction,
    KeyType,
    # Encryption
    UsageEncryption,
    OperationMode,
    EncryptionAlgorithmCoded,
    AlgorithmParameterName,
    AlgorithmParameterIVName,
    # Balance/Amount
    CreditDebit,
    # System
    SynchronizationMode,
    SystemIDStatus,
    UPDUsage,
    Language,
    ServiceType,
    # TAN
    TANMediaType,
    TANMediaClass,
    TANMediumStatus,
    TANTimeDialogAssociation,
    AllowedFormat,
    TANUsageOption,
    TANListNumberRequired,
    InitializationMode,
    DescriptionRequired,
    SMSChargeAccountRequired,
    PrincipalAccountRequired,
    TaskHashAlgorithm,
    # Versioned aliases
    Language2,
    TANMediaType2,
    TANMediaClass3,
    TANMediaClass4,
    # Statement
    StatementFormat,
    Confirmation,
)
from .identifiers import (
    BankIdentifier,
    AccountIdentifier,
    AccountInternational,
    AccountInternationalSEPA,
    COUNTRY_ALPHA_TO_NUMERIC,
    COUNTRY_NUMERIC_TO_ALPHA,
    SEPAAccount,
)
from .amounts import (
    Amount,
    Balance,
    BalanceSimple,
    Holding,
    Timestamp,
)
from .security import (
    SecurityProfile,
    SecurityIdentificationDetails,
    SecurityDateTime,
    EncryptionAlgorithm,
    HashAlgorithm,
    SignatureAlgorithm,
    KeyName,
    Certificate,
    UserDefinedSignature,
)
from .responses import (
    Response,
    ReferenceMessage,
)
from .tan import (
    TANMediaBase,
    TANMedia4,
    TANMedia5,
    ChallengeValidUntil,
    ParameterChallengeClass,
    ResponseHHDUC,
    TwoStepTANSubmission,
)
from .transactions import (
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
)
from .parameters import (
    SupportedLanguages,
    SupportedHBCIVersions,
    CommunicationParameter,
    CommunicationAccess,
    AccountLimit,
    AllowedTransaction,
    AccountInformation,
    GetSEPAAccountParameter,
)

__all__ = [
    # Base enum classes
    "FinTSEnum",
    "FinTSIntEnum",
    # Constants
    "CUSTOMER_ID_ANONYMOUS",
    # Enums - Security
    "SecurityMethod",
    "IdentifiedRole",
    "DateTimeType",
    "SecurityRole",
    "SecurityApplicationArea",
    "CompressionFunction",
    "KeyType",
    # Enums - Encryption
    "UsageEncryption",
    "OperationMode",
    "EncryptionAlgorithmCoded",
    "AlgorithmParameterName",
    "AlgorithmParameterIVName",
    # Enums - Balance/Amount
    "CreditDebit",
    # Enums - System
    "SynchronizationMode",
    "SystemIDStatus",
    "UPDUsage",
    "Language",
    "ServiceType",
    # Enums - TAN
    "TANMediaType",
    "TANMediaClass",
    "TANMediumStatus",
    "TANTimeDialogAssociation",
    "AllowedFormat",
    "TANUsageOption",
    "TANListNumberRequired",
    "InitializationMode",
    "DescriptionRequired",
    "SMSChargeAccountRequired",
    "PrincipalAccountRequired",
    "TaskHashAlgorithm",
    # Enums - Versioned aliases
    "Language2",
    "TANMediaType2",
    "TANMediaClass3",
    "TANMediaClass4",
    # Enums - Statement
    "StatementFormat",
    "Confirmation",
    # Identifiers
    "BankIdentifier",
    "AccountIdentifier",
    "AccountInternational",
    "AccountInternationalSEPA",
    "COUNTRY_ALPHA_TO_NUMERIC",
    "COUNTRY_NUMERIC_TO_ALPHA",
    "SEPAAccount",
    # Amounts
    "Amount",
    "Balance",
    "BalanceSimple",
    "Holding",
    "Timestamp",
    # Security
    "SecurityProfile",
    "SecurityIdentificationDetails",
    "SecurityDateTime",
    "EncryptionAlgorithm",
    "HashAlgorithm",
    "SignatureAlgorithm",
    "KeyName",
    "Certificate",
    "UserDefinedSignature",
    # Responses
    "Response",
    "ReferenceMessage",
    # TAN
    "TANMediaBase",
    "TANMedia4",
    "TANMedia5",
    "ChallengeValidUntil",
    "ParameterChallengeClass",
    "ResponseHHDUC",
    "TwoStepTANSubmission",
    # Transactions
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
    # Parameters
    "SupportedLanguages",
    "SupportedHBCIVersions",
    "CommunicationParameter",
    "CommunicationAccess",
    "AccountLimit",
    "AllowedTransaction",
    "AccountInformation",
    "GetSEPAAccountParameter",
]

