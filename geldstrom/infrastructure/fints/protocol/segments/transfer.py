"""FinTS SEPA Transfer Segments.

These segments handle SEPA credit transfers:
- Single transfers (HKCCS, HKIPZ)
- Batch transfers (HKCCM, HKIPM)
- Transfer parameters (HICCMS)
"""
from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from ..base import FinTSSegment, FinTSDataElementGroup
from ..types import (
    FinTSAlphanumeric,
    FinTSBinary,
    FinTSBool,
    FinTSNumeric,
)
from ..formals import (
    AccountInternational,
    Amount,
)
from .pintan import ParameterSegmentBase


# =============================================================================
# Transfer Parameter DEGs
# =============================================================================


class BatchTransferParameter(FinTSDataElementGroup):
    """Parameter SEPA-Sammelüberweisung.

    Defines limits and requirements for batch SEPA transfers.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    max_transfer_count: FinTSNumeric = Field(
        ge=0,
        lt=10000000,
        description="Maximale Anzahl CreditTransferTransactionInformation",
    )
    sum_amount_required: FinTSBool = Field(
        description="Summenfeld benötigt",
    )
    single_booking_allowed: FinTSBool = Field(
        description="Einzelbuchung erlaubt",
    )


# =============================================================================
# Single Transfer Segments
# =============================================================================


class HKCCS1(FinTSSegment):
    """SEPA Einzelüberweisung (Single SEPA Credit Transfer), version 1.

    Initiates a single SEPA credit transfer.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    SEGMENT_TYPE: ClassVar[str] = "HKCCS"
    SEGMENT_VERSION: ClassVar[int] = 1

    account: AccountInternational = Field(
        description="Kontoverbindung international",
    )
    sepa_descriptor: FinTSAlphanumeric = Field(
        max_length=256,
        description="SEPA Descriptor (pain.* URN)",
    )
    sepa_pain_message: FinTSBinary = Field(
        description="SEPA pain message (XML)",
    )


class HKIPZ1(FinTSSegment):
    """SEPA-instant Einzelüberweisung (Instant Single Transfer), version 1.

    Initiates a single SEPA instant credit transfer.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    SEGMENT_TYPE: ClassVar[str] = "HKIPZ"
    SEGMENT_VERSION: ClassVar[int] = 1

    account: AccountInternational = Field(
        description="Kontoverbindung international",
    )
    sepa_descriptor: FinTSAlphanumeric = Field(
        max_length=256,
        description="SEPA Descriptor (pain.* URN)",
    )
    sepa_pain_message: FinTSBinary = Field(
        description="SEPA pain message (XML)",
    )


# =============================================================================
# Batch Transfer Segments
# =============================================================================


class HKCCM1(FinTSSegment):
    """SEPA-Sammelüberweisung (Batch SEPA Credit Transfer), version 1.

    Initiates a batch of SEPA credit transfers.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    SEGMENT_TYPE: ClassVar[str] = "HKCCM"
    SEGMENT_VERSION: ClassVar[int] = 1

    account: AccountInternational = Field(
        description="Kontoverbindung international",
    )
    sum_amount: Amount = Field(
        description="Summenfeld",
    )
    request_single_booking: FinTSBool = Field(
        description="Einzelbuchung gewünscht",
    )
    sepa_descriptor: FinTSAlphanumeric = Field(
        max_length=256,
        description="SEPA Descriptor (pain.* URN)",
    )
    sepa_pain_message: FinTSBinary = Field(
        description="SEPA pain message (XML)",
    )


class HKIPM1(FinTSSegment):
    """SEPA-instant Sammelüberweisung (Instant Batch Transfer), version 1.

    Initiates a batch of SEPA instant credit transfers.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    SEGMENT_TYPE: ClassVar[str] = "HKIPM"
    SEGMENT_VERSION: ClassVar[int] = 1

    account: AccountInternational = Field(
        description="Kontoverbindung international",
    )
    sum_amount: Amount = Field(
        description="Summenfeld",
    )
    request_single_booking: FinTSBool = Field(
        description="Einzelbuchung gewünscht",
    )
    sepa_descriptor: FinTSAlphanumeric = Field(
        max_length=256,
        description="SEPA Descriptor (pain.* URN)",
    )
    sepa_pain_message: FinTSBinary = Field(
        description="SEPA pain message (XML)",
    )


# =============================================================================
# Parameter Segments
# =============================================================================


class HICCMS1(ParameterSegmentBase):
    """SEPA-Sammelüberweisung Parameter (Batch Transfer Parameters), version 1.

    Contains parameters for batch SEPA transfers.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    SEGMENT_TYPE: ClassVar[str] = "HICCMS"
    SEGMENT_VERSION: ClassVar[int] = 1

    parameter: BatchTransferParameter = Field(
        description="Parameter SEPA-Sammelüberweisung",
    )


# =============================================================================
# Version Registries
# =============================================================================


HKCCS_VERSIONS: dict[int, type[FinTSSegment]] = {
    1: HKCCS1,
}

HKIPZ_VERSIONS: dict[int, type[FinTSSegment]] = {
    1: HKIPZ1,
}

HKCCM_VERSIONS: dict[int, type[FinTSSegment]] = {
    1: HKCCM1,
}

HKIPM_VERSIONS: dict[int, type[FinTSSegment]] = {
    1: HKIPM1,
}

HICCMS_VERSIONS: dict[int, type[FinTSSegment]] = {
    1: HICCMS1,
}


__all__ = [
    # DEGs
    "BatchTransferParameter",
    # Single transfers
    "HKCCS1",
    "HKIPZ1",
    "HKCCS_VERSIONS",
    "HKIPZ_VERSIONS",
    # Batch transfers
    "HKCCM1",
    "HKIPM1",
    "HKCCM_VERSIONS",
    "HKIPM_VERSIONS",
    # Parameters
    "HICCMS1",
    "HICCMS_VERSIONS",
]

