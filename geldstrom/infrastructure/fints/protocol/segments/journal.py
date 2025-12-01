"""FinTS Status Protocol (Journal) Segments.

These segments handle status protocol (journal) information:
- Status protocol requests (HKPRO)
- Status protocol responses (HIPRO)
- Status protocol parameters (HIPROS)
"""
from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from ..base import FinTSSegment
from ..types import (
    FinTSAlphanumeric,
    FinTSDate,
    FinTSNumeric,
    FinTSTime,
)
from ..formals import (
    ReferenceMessage,
    Response,
)
from .pintan import ParameterSegmentBase


# =============================================================================
# Status Protocol Request Segments
# =============================================================================


class HKPRO3(FinTSSegment):
    """Statusprotokoll anfordern (Request Status Protocol), version 3.

    Requests the bank's status protocol/journal.

    Source: FinTS 3.0 Formals
    """

    SEGMENT_TYPE: ClassVar[str] = "HKPRO"
    SEGMENT_VERSION: ClassVar[int] = 3

    date_start: FinTSDate | None = Field(
        default=None,
        description="Von Datum",
    )
    date_end: FinTSDate | None = Field(
        default=None,
        description="Bis Datum",
    )
    max_number_responses: FinTSNumeric | None = Field(
        default=None,
        ge=0,
        lt=10000,
        description="Maximale Anzahl Einträge",
    )
    touchdown_point: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=35,
        description="Aufsetzpunkt",
    )


class HKPRO4(FinTSSegment):
    """Statusprotokoll anfordern (Request Status Protocol), version 4.

    Requests the bank's status protocol/journal.

    Source: FinTS 3.0 Formals
    """

    SEGMENT_TYPE: ClassVar[str] = "HKPRO"
    SEGMENT_VERSION: ClassVar[int] = 4

    date_start: FinTSDate | None = Field(
        default=None,
        description="Von Datum",
    )
    date_end: FinTSDate | None = Field(
        default=None,
        description="Bis Datum",
    )
    max_number_responses: FinTSNumeric | None = Field(
        default=None,
        ge=0,
        lt=10000,
        description="Maximale Anzahl Einträge",
    )
    touchdown_point: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=35,
        description="Aufsetzpunkt",
    )


# =============================================================================
# Status Protocol Response Segments
# =============================================================================


class HIPRO3(FinTSSegment):
    """Statusprotokoll rückmelden (Status Protocol Response), version 3.

    Returns status protocol/journal entries.

    Source: FinTS 3.0 Formals
    """

    SEGMENT_TYPE: ClassVar[str] = "HIPRO"
    SEGMENT_VERSION: ClassVar[int] = 3

    reference_message: ReferenceMessage = Field(
        description="Bezugsnachricht",
    )
    reference: FinTSNumeric | None = Field(
        default=None,
        ge=0,
        lt=1000,
        description="Bezugssegment",
    )
    date: FinTSDate = Field(
        description="Datum",
    )
    time: FinTSTime = Field(
        description="Uhrzeit",
    )
    responses: list[Response] = Field(
        min_length=1,
        description="Rückmeldungen",
    )


class HIPRO4(FinTSSegment):
    """Statusprotokoll rückmelden (Status Protocol Response), version 4.

    Returns status protocol/journal entries.

    Source: FinTS 3.0 Formals
    """

    SEGMENT_TYPE: ClassVar[str] = "HIPRO"
    SEGMENT_VERSION: ClassVar[int] = 4

    reference_message: ReferenceMessage = Field(
        description="Bezugsnachricht",
    )
    reference: FinTSNumeric | None = Field(
        default=None,
        ge=0,
        lt=1000,
        description="Bezugssegment",
    )
    date: FinTSDate = Field(
        description="Datum",
    )
    time: FinTSTime = Field(
        description="Uhrzeit",
    )
    responses: list[Response] = Field(
        min_length=1,
        description="Rückmeldungen",
    )


# =============================================================================
# Status Protocol Parameter Segments
# =============================================================================


class ParameterSegment22Base(FinTSSegment):
    """Base class for version 2/2 parameter segments (without security_class)."""

    max_number_tasks: FinTSNumeric = Field(
        ge=0,
        lt=1000,
        description="Maximale Anzahl Aufträge",
    )
    min_number_signatures: FinTSNumeric = Field(
        ge=0,
        lt=10,
        description="Anzahl Signaturen mindestens",
    )


class HIPROS3(ParameterSegment22Base):
    """Statusprotokoll Parameter (Status Protocol Parameters), version 3.

    Contains parameters for status protocol requests.

    Source: FinTS 3.0 Formals
    """

    SEGMENT_TYPE: ClassVar[str] = "HIPROS"
    SEGMENT_VERSION: ClassVar[int] = 3


class HIPROS4(ParameterSegmentBase):
    """Statusprotokoll Parameter (Status Protocol Parameters), version 4.

    Contains parameters for status protocol requests.

    Source: FinTS 3.0 Formals
    """

    SEGMENT_TYPE: ClassVar[str] = "HIPROS"
    SEGMENT_VERSION: ClassVar[int] = 4


# =============================================================================
# Version Registries
# =============================================================================


HKPRO_VERSIONS: dict[int, type[FinTSSegment]] = {
    3: HKPRO3,
    4: HKPRO4,
}

HIPRO_VERSIONS: dict[int, type[FinTSSegment]] = {
    3: HIPRO3,
    4: HIPRO4,
}

HIPROS_VERSIONS: dict[int, type[FinTSSegment]] = {
    3: HIPROS3,
    4: HIPROS4,
}


__all__ = [
    # Request
    "HKPRO3",
    "HKPRO4",
    "HKPRO_VERSIONS",
    # Response
    "HIPRO3",
    "HIPRO4",
    "HIPRO_VERSIONS",
    # Parameters
    "ParameterSegment22Base",
    "HIPROS3",
    "HIPROS4",
    "HIPROS_VERSIONS",
]

