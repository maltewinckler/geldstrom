"""FinTS Message Security Segments.

These segments handle message-level security including:
- Encryption header (HNVSK)
- Encrypted data container (HNVSD)
- Signature header (HNSHK)
- Signature trailer (HNSHA)
"""
from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from ..base import FinTSSegment, SegmentSequence
from ..types import (
    FinTSAlphanumeric,
    FinTSBinary,
    FinTSCode,
    FinTSNumeric,
)
from ..formals import (
    Certificate,
    CompressionFunction,
    EncryptionAlgorithm,
    HashAlgorithm,
    KeyName,
    SecurityApplicationArea,
    SecurityDateTime,
    SecurityIdentificationDetails,
    SecurityProfile,
    SecurityRole,
    SignatureAlgorithm,
    UserDefinedSignature,
)


# =============================================================================
# Encryption Segments
# =============================================================================


class HNVSK3(FinTSSegment):
    """Verschlüsselungskopf (Encryption Header), version 3.

    Contains encryption metadata for the message.

    Source: FinTS 3.0 Sicherheitsverfahren HBCI
    """

    SEGMENT_TYPE: ClassVar[str] = "HNVSK"
    SEGMENT_VERSION: ClassVar[int] = 3

    security_profile: SecurityProfile = Field(
        description="Sicherheitsprofil",
    )
    security_function: FinTSCode = Field(
        description="Sicherheitsfunktion, kodiert",
    )
    security_role: SecurityRole = Field(
        description="Rolle des Sicherheitslieferanten, kodiert",
    )
    security_identification_details: SecurityIdentificationDetails = Field(
        description="Sicherheitsidentifikation, Details",
    )
    security_datetime: SecurityDateTime = Field(
        description="Sicherheitsdatum und -uhrzeit",
    )
    encryption_algorithm: EncryptionAlgorithm = Field(
        description="Verschlüsselungsalgorithmus",
    )
    key_name: KeyName = Field(
        description="Schlüsselname",
    )
    compression_function: CompressionFunction = Field(
        description="Komprimierungsfunktion",
    )
    certificate: Certificate | None = Field(
        default=None,
        description="Zertifikat",
    )


class HNVSD1(FinTSSegment):
    """Verschlüsselte Daten (Encrypted Data Container), version 1.

    Contains the encrypted message payload.

    Source: FinTS 3.0 Sicherheitsverfahren HBCI
    """

    SEGMENT_TYPE: ClassVar[str] = "HNVSD"
    SEGMENT_VERSION: ClassVar[int] = 1

    data: FinTSBinary = Field(
        description="Daten, verschlüsselt (contains nested segments)",
    )

    _parsed_segments: "SegmentSequence | None" = None

    @property
    def segments(self) -> "SegmentSequence":
        """Parse and return the nested segments from the data field.

        This allows find_segments to recurse into the encrypted data.
        """
        if self._parsed_segments is None:
            from geldstrom.types import SegmentSequence
            if isinstance(self.data, bytes):
                self._parsed_segments = SegmentSequence(self.data)
            else:
                self._parsed_segments = SegmentSequence([])
        return self._parsed_segments

    def find_segments(self, *args, **kwargs):
        """Delegate segment search to the inner segments."""
        return self.segments.find_segments(*args, **kwargs)


# =============================================================================
# Signature Segments
# =============================================================================


class HNSHK4(FinTSSegment):
    """Signaturkopf (Signature Header), version 4.

    Contains signature metadata and starts the signed area.

    Source: FinTS 3.0 Sicherheitsverfahren HBCI
    """

    SEGMENT_TYPE: ClassVar[str] = "HNSHK"
    SEGMENT_VERSION: ClassVar[int] = 4

    security_profile: SecurityProfile = Field(
        description="Sicherheitsprofil",
    )
    security_function: FinTSCode = Field(
        description="Sicherheitsfunktion, kodiert",
    )
    security_reference: FinTSAlphanumeric = Field(
        max_length=14,
        description="Sicherheitskontrollreferenz",
    )
    security_application_area: SecurityApplicationArea = Field(
        description="Bereich der Sicherheitsapplikation, kodiert",
    )
    security_role: SecurityRole = Field(
        description="Rolle des Sicherheitslieferanten, kodiert",
    )
    security_identification_details: SecurityIdentificationDetails = Field(
        description="Sicherheitsidentifikation, Details",
    )
    security_reference_number: FinTSNumeric = Field(
        description="Sicherheitsreferenznummer",
    )
    security_datetime: SecurityDateTime = Field(
        description="Sicherheitsdatum und -uhrzeit",
    )
    hash_algorithm: HashAlgorithm = Field(
        description="Hashalgorithmus",
    )
    signature_algorithm: SignatureAlgorithm = Field(
        description="Signaturalgorithmus",
    )
    key_name: KeyName = Field(
        description="Schlüsselname",
    )
    certificate: Certificate | None = Field(
        default=None,
        description="Zertifikat",
    )


class HNSHA2(FinTSSegment):
    """Signaturabschluss (Signature Trailer), version 2.

    Closes the signed area and contains the signature.

    Source: FinTS 3.0 Sicherheitsverfahren HBCI
    """

    SEGMENT_TYPE: ClassVar[str] = "HNSHA"
    SEGMENT_VERSION: ClassVar[int] = 2

    security_reference: FinTSAlphanumeric = Field(
        max_length=14,
        description="Sicherheitskontrollreferenz",
    )
    validation_result: FinTSBinary | None = Field(
        default=None,
        description="Validierungsresultat",
    )
    user_defined_signature: UserDefinedSignature | None = Field(
        default=None,
        description="Benutzerdefinierte Signatur",
    )


# =============================================================================
# Version Registries
# =============================================================================


HNVSK_VERSIONS: dict[int, type[FinTSSegment]] = {
    3: HNVSK3,
}

HNVSD_VERSIONS: dict[int, type[FinTSSegment]] = {
    1: HNVSD1,
}

HNSHK_VERSIONS: dict[int, type[FinTSSegment]] = {
    4: HNSHK4,
}

HNSHA_VERSIONS: dict[int, type[FinTSSegment]] = {
    2: HNSHA2,
}


__all__ = [
    # Encryption
    "HNVSK3",
    "HNVSD1",
    "HNVSK_VERSIONS",
    "HNVSD_VERSIONS",
    # Signature
    "HNSHK4",
    "HNSHA2",
    "HNSHK_VERSIONS",
    "HNSHA_VERSIONS",
]

