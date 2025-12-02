"""FinTS Security DEGs.

These DEGs handle security-related information in FinTS messages,
including encryption, signatures, and authentication.
"""

from __future__ import annotations

from pydantic import Field

from ..base import FinTSDataElementGroup
from ..types import (
    FinTSAlphanumeric,
    FinTSBinary,
    FinTSCode,
    FinTSDate,
    FinTSID,
    FinTSNumeric,
    FinTSTime,
)
from .enums import (
    AlgorithmParameterIVName,
    AlgorithmParameterName,
    DateTimeType,
    EncryptionAlgorithmCoded,
    IdentifiedRole,
    KeyType,
    OperationMode,
    SecurityMethod,
    UsageEncryption,
)
from .identifiers import BankIdentifier


class SecurityProfile(FinTSDataElementGroup):
    """Sicherheitsprofil (Security Profile).

    Identifies the security method and version used for a message.

    Source: FinTS 3.0 Formals

    Example:
        profile = SecurityProfile(
            security_method=SecurityMethod.PIN,
            security_method_version=1,
        )
    """

    security_method: SecurityMethod = Field(
        description="Sicherheitsverfahren",
    )
    security_method_version: FinTSNumeric = Field(
        description="Version des Sicherheitsverfahrens",
    )


class SecurityIdentificationDetails(FinTSDataElementGroup):
    """Sicherheitsidentifikation, Details (Security Identification Details).

    Identifies the party providing security for the message.

    Source: FinTS 3.0 Formals

    Note: identifier may be omitted in bank responses when the message
    is not signed (e.g., some banks like DKB).
    """

    identified_role: IdentifiedRole = Field(
        description="Rolle des Identifizierten",
    )
    cid: FinTSBinary | None = Field(
        default=None,
        max_length=256,
        description="CID (Certificate Identifier)",
    )
    identifier: FinTSID | None = Field(
        default=None,
        description="Identifizierer (may be omitted in unsigned bank responses)",
    )


class SecurityDateTime(FinTSDataElementGroup):
    """Sicherheitsdatum und -uhrzeit (Security Date/Time).

    Timestamp for security purposes.

    Source: FinTS 3.0 Formals
    """

    date_time_type: DateTimeType = Field(
        description="Datum/Uhrzeit-Typ",
    )
    date: FinTSDate | None = Field(
        default=None,
        description="Datum",
    )
    time: FinTSTime | None = Field(
        default=None,
        description="Uhrzeit",
    )


class EncryptionAlgorithm(FinTSDataElementGroup):
    """Verschlüsselungsalgorithmus (Encryption Algorithm).

    Specifies the encryption algorithm and parameters.

    Source: FinTS 3.0 Formals
    """

    usage_encryption: UsageEncryption = Field(
        description="Verwendung der Verschlüsselung",
    )
    operation_mode: OperationMode = Field(
        description="Operationsmodus",
    )
    encryption_algorithm: EncryptionAlgorithmCoded = Field(
        description="Verschlüsselungsalgorithmus, kodiert",
    )
    algorithm_parameter_value: FinTSBinary = Field(
        max_length=512,
        description="Algorithmusparameterwert",
    )
    algorithm_parameter_name: AlgorithmParameterName = Field(
        description="Algorithmusparameter, Name",
    )
    algorithm_parameter_iv_name: AlgorithmParameterIVName = Field(
        description="Algorithmusparameter IV, Name",
    )
    algorithm_parameter_iv_value: FinTSBinary | None = Field(
        default=None,
        max_length=512,
        description="Algorithmusparameter IV, Wert",
    )


class HashAlgorithm(FinTSDataElementGroup):
    """Hash-Algorithmus (Hash Algorithm).

    Specifies the hash algorithm for signatures.

    Source: FinTS 3.0 Formals
    """

    usage_hash: FinTSCode = Field(
        max_length=3,
        description="Verwendung des Hashwertes",
    )
    hash_algorithm: FinTSCode = Field(
        max_length=3,
        description="Hash-Algorithmus, kodiert",
    )
    algorithm_parameter_name: FinTSCode = Field(
        max_length=3,
        description="Algorithmusparameter, Name",
    )
    algorithm_parameter_value: FinTSBinary | None = Field(
        default=None,
        max_length=512,
        description="Algorithmusparameterwert",
    )


class SignatureAlgorithm(FinTSDataElementGroup):
    """Signaturalgorithmus (Signature Algorithm).

    Specifies the signature algorithm for message authentication.

    Source: FinTS 3.0 Formals
    """

    usage_signature: FinTSCode = Field(
        max_length=3,
        description="Verwendung der Signatur",
    )
    signature_algorithm: FinTSCode = Field(
        max_length=3,
        description="Signaturalgorithmus, kodiert",
    )
    operation_mode: FinTSCode = Field(
        max_length=3,
        description="Operationsmodus",
    )


class KeyName(FinTSDataElementGroup):
    """Schlüsselname (Key Name).

    Identifies a cryptographic key.

    Source: FinTS 3.0 Formals
    """

    bank_identifier: BankIdentifier = Field(
        description="Kreditinstitutskennung",
    )
    user_id: FinTSID = Field(
        description="Benutzerkennung",
    )
    key_type: KeyType = Field(
        description="Schlüsselart",
    )
    key_number: FinTSNumeric = Field(
        ge=0,
        lt=1000,  # max 3 digits
        description="Schlüsselnummer",
    )
    key_version: FinTSNumeric = Field(
        ge=0,
        lt=1000,  # max 3 digits
        description="Schlüsselversion",
    )


class Certificate(FinTSDataElementGroup):
    """Zertifikat (Certificate).

    Contains a cryptographic certificate.

    Source: FinTS 3.0 Formals
    """

    certificate_type: FinTSCode = Field(
        description="Zertifikatstyp",
    )
    certificate_content: FinTSBinary = Field(
        max_length=4096,
        description="Zertifikatsinhalt",
    )


class UserDefinedSignature(FinTSDataElementGroup):
    """Benutzerdefinierte Signatur (User Defined Signature).

    Contains PIN and optional TAN for PIN/TAN authentication.

    Source: FinTS 3.0 Sicherheitsverfahren PIN/TAN
    """

    pin: FinTSAlphanumeric = Field(
        max_length=99,
        description="PIN",
    )
    tan: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=99,
        description="TAN",
    )


__all__ = [
    "SecurityProfile",
    "SecurityIdentificationDetails",
    "SecurityDateTime",
    "EncryptionAlgorithm",
    "HashAlgorithm",
    "SignatureAlgorithm",
    "KeyName",
    "Certificate",
    "UserDefinedSignature",
]
