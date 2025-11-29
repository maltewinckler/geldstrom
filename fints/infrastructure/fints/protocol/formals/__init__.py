"""FinTS Formal Data Element Groups (DEGs) - Pydantic models.

This module provides Pydantic-based implementations of FinTS DEGs,
replacing the legacy Container-based definitions in fints/formals.py.

Organization:
- enums: All FinTS enumeration types
- identifiers: Bank and account identifiers
- amounts: Amount and balance types
- security: Security-related DEGs
- responses: Response message types
"""
from __future__ import annotations

from .enums import (
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
)
from .amounts import (
    Amount,
    Balance,
    BalanceSimple,
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
    UserDefinedSignature,
)
from .responses import (
    Response,
    ReferenceMessage,
)

__all__ = [
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
    # Amounts
    "Amount",
    "Balance",
    "BalanceSimple",
    "Timestamp",
    # Security
    "SecurityProfile",
    "SecurityIdentificationDetails",
    "SecurityDateTime",
    "EncryptionAlgorithm",
    "HashAlgorithm",
    "SignatureAlgorithm",
    "KeyName",
    "UserDefinedSignature",
    # Responses
    "Response",
    "ReferenceMessage",
]

