"""FinTS transaction-related DEGs (CAMT statements, SEPA transfer parameters)."""

from __future__ import annotations

from pydantic import Field

from ..base import FinTSDataElementGroup
from ..types import (
    FinTSAlphanumeric,
    FinTSBinary,
    FinTSBool,
    FinTSNumeric,
)


class SupportedMessageTypes(FinTSDataElementGroup):
    """Unterstützte camt-Messages - CAMT formats supported by the bank."""

    expected_type: list[FinTSAlphanumeric] = Field(
        min_length=1,
        max_length=99,
        description="Unterstützte camt-messages (URNs)",
    )


class BookedCamtStatements(FinTSDataElementGroup):
    """Gebuchte camt-Umsätze - booked transactions in CAMT XML format."""

    camt_statements: list[FinTSBinary] = Field(
        min_length=1,
        description="camt-Umsätze (XML)",
    )


class SupportedSEPAPainMessages(FinTSDataElementGroup):
    """Unterstützte SEPA pain messages - pain.* formats supported for transfers."""

    sepa_descriptors: list[FinTSAlphanumeric] = Field(
        max_length=99,
        description="SEPA Descriptor (pain.* URNs)",
    )


class BatchTransferParameter(FinTSDataElementGroup):
    """Parameter SEPA-Sammelüberweisung - limits and requirements for batch SEPA transfers."""

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


__all__ = [
    "SupportedMessageTypes",
    "BookedCamtStatements",
    "SupportedSEPAPainMessages",
    "BatchTransferParameter",
]
