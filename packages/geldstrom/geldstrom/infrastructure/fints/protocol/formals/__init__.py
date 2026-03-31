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

from .amounts import (
    Amount,
    Balance,
    BalanceSimple,
    Holding,
    Timestamp,
)
from .enums import (
    AlgorithmParameterIVName,
    AlgorithmParameterName,
    AllowedFormat,
    CompressionFunction,
    Confirmation,
    # Balance/Amount
    CreditDebit,
    DateTimeType,
    DescriptionRequired,
    EncryptionAlgorithmCoded,
    # Base classes
    FinTSEnum,
    FinTSIntEnum,
    IdentifiedRole,
    InitializationMode,
    KeyType,
    Language,
    # Versioned aliases
    Language2,
    OperationMode,
    PrincipalAccountRequired,
    SecurityApplicationArea,
    # Security
    SecurityMethod,
    SecurityRole,
    ServiceType,
    SMSChargeAccountRequired,
    # System
    SynchronizationMode,
    SystemIDStatus,
    TANListNumberRequired,
    TANMediaClass,
    TANMediaClass3,
    TANMediaClass4,
    # TAN
    TANMediaType,
    TANMediaType2,
    TANMediumStatus,
    TANTimeDialogAssociation,
    TANUsageOption,
    TaskHashAlgorithm,
    UPDUsage,
    # Encryption
    UsageEncryption,
)
from .identifiers import (
    COUNTRY_ALPHA_TO_NUMERIC,
    COUNTRY_NUMERIC_TO_ALPHA,
    AccountIdentifier,
    AccountInternational,
    AccountInternationalSEPA,
    BankIdentifier,
    SEPAAccount,
)
from .parameters import (
    AccountInformation,
    AccountLimit,
    AllowedTransaction,
    CommunicationAccess,
    CommunicationParameter,
    GetSEPAAccountParameter,
    SupportedHBCIVersions,
    SupportedLanguages,
)
from .responses import (
    ReferenceMessage,
    Response,
)
from .security import (
    Certificate,
    EncryptionAlgorithm,
    HashAlgorithm,
    KeyName,
    SecurityDateTime,
    SecurityIdentificationDetails,
    SecurityProfile,
    SignatureAlgorithm,
    UserDefinedSignature,
)
from .tan import (
    ChallengeValidUntil,
    ParameterChallengeClass,
    ResponseHHDUC,
    TANMedia4,
    TANMedia5,
    TANMediaBase,
)
from .transactions import (
    BatchTransferParameter,
    BookedCamtStatements,
    SupportedMessageTypes,
    SupportedSEPAPainMessages,
)

# Constants
CUSTOMER_ID_ANONYMOUS = "9999999999"

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
    # Transactions
    "SupportedMessageTypes",
    "BookedCamtStatements",
    "SupportedSEPAPainMessages",
    "BatchTransferParameter",
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
