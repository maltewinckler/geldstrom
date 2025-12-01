"""FinTS Dialog Segments.

These segments handle dialog management including:
- Message header/trailer (HNHBK, HNHBS)
- Responses (HIRMG, HIRMS)
- Synchronization (HKSYN, HISYN)
- Dialog end (HKEND)
"""
from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from ..base import FinTSSegment
from ..types import (
    FinTSAlphanumeric,
    FinTSID,
    FinTSNumeric,
)
from ..formals import (
    ReferenceMessage,
    Response,
    SynchronizationMode,
)


# =============================================================================
# Message Header/Trailer Segments
# =============================================================================


class HNHBK3(FinTSSegment):
    """Nachrichtenkopf (Message Header), version 3.

    The first segment of every FinTS message containing:
    - Total message size
    - Protocol version
    - Dialog identification
    - Message number

    Source: FinTS 3.0 Formals
    """

    SEGMENT_TYPE: ClassVar[str] = "HNHBK"
    SEGMENT_VERSION: ClassVar[int] = 3

    message_size: FinTSNumeric = Field(
        description="Größe der Nachricht (nach Verschlüsselung und Komprimierung)",
    )
    hbci_version: FinTSNumeric = Field(
        ge=0,
        lt=1000,
        description="HBCI-Version (e.g., 300 for FinTS 3.0)",
    )
    dialog_id: FinTSID = Field(
        description="Dialog-ID",
    )
    message_number: FinTSNumeric = Field(
        ge=0,
        lt=10000,
        description="Nachrichtennummer",
    )
    reference_message: ReferenceMessage | None = Field(
        default=None,
        description="Bezugsnachricht",
    )

    def to_wire_list(self) -> list:
        """Serialize to wire format with special handling for message_size.

        message_size must be exactly 12 digits zero-padded.
        """
        result = super().to_wire_list()
        # message_size is at index 1 (after header at index 0)
        if len(result) > 1:
            result[1] = f"{int(result[1]):012d}"
        return result


class HNHBS1(FinTSSegment):
    """Nachrichtenabschluss (Message Trailer), version 1.

    The last segment of every FinTS message.

    Source: FinTS 3.0 Formals
    """

    SEGMENT_TYPE: ClassVar[str] = "HNHBS"
    SEGMENT_VERSION: ClassVar[int] = 1

    message_number: FinTSNumeric = Field(
        ge=0,
        lt=10000,
        description="Nachrichtennummer",
    )


# =============================================================================
# Response Segments
# =============================================================================


class HIRMG2(FinTSSegment):
    """Rückmeldungen zur Gesamtnachricht (Global Message Responses), version 2.

    Contains response codes for the entire message.

    Source: FinTS 3.0 Formals
    """

    SEGMENT_TYPE: ClassVar[str] = "HIRMG"
    SEGMENT_VERSION: ClassVar[int] = 2

    responses: list[Response] = Field(
        min_length=1,
        max_length=99,
        description="Rückmeldungen",
    )


class HIRMS2(FinTSSegment):
    """Rückmeldungen zu Segmenten (Segment Responses), version 2.

    Contains response codes for specific segments.

    Source: FinTS 3.0 Formals
    """

    SEGMENT_TYPE: ClassVar[str] = "HIRMS"
    SEGMENT_VERSION: ClassVar[int] = 2

    responses: list[Response] = Field(
        min_length=1,
        max_length=99,
        description="Rückmeldungen",
    )


# =============================================================================
# Synchronization Segments
# =============================================================================


class HKSYN3(FinTSSegment):
    """Synchronisierung (Synchronization Request), version 3.

    Requests synchronization with the bank to obtain system ID.

    Source: FinTS 3.0 Formals
    """

    SEGMENT_TYPE: ClassVar[str] = "HKSYN"
    SEGMENT_VERSION: ClassVar[int] = 3

    synchronization_mode: SynchronizationMode = Field(
        description="Synchronisierungsmodus",
    )


class HISYN4(FinTSSegment):
    """Synchronisierungsantwort (Synchronization Response), version 4.

    Response containing the assigned system ID.

    Source: FinTS 3.0 Formals
    """

    SEGMENT_TYPE: ClassVar[str] = "HISYN"
    SEGMENT_VERSION: ClassVar[int] = 4

    system_id: FinTSID = Field(
        description="Kundensystem-ID",
    )
    message_number: FinTSNumeric | None = Field(
        default=None,
        ge=0,
        lt=10000,
        description="Nachrichtennummer",
    )
    security_reference_signature_key: FinTSNumeric | None = Field(
        default=None,
        description="Sicherheitsreferenznummer für Signierschlüssel",
    )
    security_reference_digital_signature: FinTSNumeric | None = Field(
        default=None,
        description="Sicherheitsreferenznummer für Digitale Signatur",
    )


# =============================================================================
# Dialog End Segment
# =============================================================================


class HKEND1(FinTSSegment):
    """Dialogende (Dialog End), version 1.

    Terminates the current dialog.

    Source: FinTS 3.0 Formals
    """

    SEGMENT_TYPE: ClassVar[str] = "HKEND"
    SEGMENT_VERSION: ClassVar[int] = 1

    dialog_id: FinTSID = Field(
        description="Dialog-ID",
    )


# =============================================================================
# Version Registries
# =============================================================================


HNHBK_VERSIONS: dict[int, type[FinTSSegment]] = {
    3: HNHBK3,
}

HNHBS_VERSIONS: dict[int, type[FinTSSegment]] = {
    1: HNHBS1,
}

HIRMG_VERSIONS: dict[int, type[FinTSSegment]] = {
    2: HIRMG2,
}

HIRMS_VERSIONS: dict[int, type[FinTSSegment]] = {
    2: HIRMS2,
}

HKSYN_VERSIONS: dict[int, type[FinTSSegment]] = {
    3: HKSYN3,
}

HISYN_VERSIONS: dict[int, type[FinTSSegment]] = {
    4: HISYN4,
}

HKEND_VERSIONS: dict[int, type[FinTSSegment]] = {
    1: HKEND1,
}


__all__ = [
    # Message header/trailer
    "HNHBK3",
    "HNHBS1",
    "HNHBK_VERSIONS",
    "HNHBS_VERSIONS",
    # Responses
    "HIRMG2",
    "HIRMS2",
    "HIRMG_VERSIONS",
    "HIRMS_VERSIONS",
    # Synchronization
    "HKSYN3",
    "HISYN4",
    "HKSYN_VERSIONS",
    "HISYN_VERSIONS",
    # Dialog end
    "HKEND1",
    "HKEND_VERSIONS",
]

