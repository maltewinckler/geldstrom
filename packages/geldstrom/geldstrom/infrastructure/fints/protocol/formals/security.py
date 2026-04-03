"""FinTS security DEGs (encryption, signatures, authentication)."""

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
    """Sicherheitsprofil (Security Profile) — security method and version."""

    security_method: SecurityMethod = Field(
        description="Sicherheitsverfahren",
    )
    security_method_version: FinTSNumeric = Field(
        description="Version des Sicherheitsverfahrens",
    )


class SecurityIdentificationDetails(FinTSDataElementGroup):
    """Sicherheitsidentifikation, Details — party providing security for the message.

    Note: identifier may be omitted in unsigned bank responses (e.g. DKB).
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
    """Sicherheitsdatum und -uhrzeit (Security Date/Time)."""

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
    """Verschlüsselungsalgorithmus (Encryption Algorithm) and parameters."""

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
    """Hash-Algorithmus (Hash Algorithm) for signatures."""

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
    """Signaturalgorithmus (Signature Algorithm) for message authentication."""

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
    """Schlüsselname (Key Name) — identifies a cryptographic key."""

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
    """Zertifikat (Certificate)."""

    certificate_type: FinTSCode = Field(
        description="Zertifikatstyp",
    )
    certificate_content: FinTSBinary = Field(
        max_length=4096,
        description="Zertifikatsinhalt",
    )


class UserDefinedSignature(FinTSDataElementGroup):
    """Benutzerdefinierte Signatur — PIN/TAN pair; repr always masks credentials."""

    pin: FinTSAlphanumeric = Field(
        max_length=99,
        description="PIN",
    )
    tan: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=99,
        description="TAN",
    )

    def __repr__(self) -> str:
        tan_repr = "'***'" if self.tan else "None"
        return f"UserDefinedSignature(pin='***', tan={tan_repr})"

    def __str__(self) -> str:
        return self.__repr__()


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
