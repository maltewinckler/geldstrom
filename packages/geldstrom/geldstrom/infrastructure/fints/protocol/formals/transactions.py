"""FinTS Transaction-related Data Element Groups (DEGs).

This module contains Pydantic models for transaction-related data structures
including CAMT statements and SEPA transfer parameters.
"""

from __future__ import annotations

from pydantic import Field

from ..base import FinTSDataElementGroup
from ..types import (
    FinTSAlphanumeric,
    FinTSBinary,
    FinTSBool,
    FinTSNumeric,
)

# =============================================================================
# CAMT/Statement DEGs
# =============================================================================


class SupportedMessageTypes(FinTSDataElementGroup):
    """Unterstützte camt-Messages.

    Lists the CAMT message formats supported by the bank.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle (SEPA)
    """

    expected_type: list[FinTSAlphanumeric] = Field(
        min_length=1,
        max_length=99,
        description="Unterstützte camt-messages (URNs)",
    )


class BookedCamtStatements(FinTSDataElementGroup):
    """Gebuchte camt-Umsätze.

    Contains booked transactions in CAMT XML format.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    camt_statements: list[FinTSBinary] = Field(
        min_length=1,
        description="camt-Umsätze (XML)",
    )


class SupportedSEPAPainMessages(FinTSDataElementGroup):
    """Unterstützte SEPA pain messages.

    Lists the SEPA pain.* message formats supported for transfers/debits.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    sepa_descriptors: list[FinTSAlphanumeric] = Field(
        max_length=99,
        description="SEPA Descriptor (pain.* URNs)",
    )


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


__all__ = [
    # CAMT/Statement
    "SupportedMessageTypes",
    "BookedCamtStatements",
    "SupportedSEPAPainMessages",
    # Transfer
    "BatchTransferParameter",
]
