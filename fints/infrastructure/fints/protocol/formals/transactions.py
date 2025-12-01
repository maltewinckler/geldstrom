"""FinTS Transaction-related Data Element Groups (DEGs).

This module contains Pydantic models for transaction-related data structures
including SEPA transfers, debits, and statement formats.
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

    statements: list[FinTSBinary] = Field(
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


# =============================================================================
# Debit Parameter DEGs
# =============================================================================


class ScheduledDebitParameter1(FinTSDataElementGroup):
    """Parameter terminierte SEPA-Einzellastschrift, version 1.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    min_advance_notice_FNAL_RCUR: FinTSNumeric = Field(
        ge=0,
        lt=10000,
        description="Minimale Vorlaufzeit FNAL/RCUR (Tage)",
    )
    max_advance_notice_FNAL_RCUR: FinTSNumeric = Field(
        ge=0,
        lt=10000,
        description="Maximale Vorlaufzeit FNAL/RCUR (Tage)",
    )
    min_advance_notice_FRST_OOFF: FinTSNumeric = Field(
        ge=0,
        lt=10000,
        description="Minimale Vorlaufzeit FRST/OOFF (Tage)",
    )
    max_advance_notice_FRST_OOFF: FinTSNumeric = Field(
        ge=0,
        lt=10000,
        description="Maximale Vorlaufzeit FRST/OOFF (Tage)",
    )


class ScheduledDebitParameter2(FinTSDataElementGroup):
    """Parameter terminierte SEPA-Einzellastschrift, version 2.

    Uses string-based advance notice specification.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    min_advance_notice: FinTSAlphanumeric = Field(
        max_length=99,
        description="Minimale Vorlaufzeit SEPA-Lastschrift",
    )
    max_advance_notice: FinTSAlphanumeric = Field(
        max_length=99,
        description="Maximale Vorlaufzeit SEPA-Lastschrift",
    )
    allowed_purpose_codes: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=4096,
        description="Zulässige purpose codes",
    )
    supported_sepa_formats: list[FinTSAlphanumeric] | None = Field(
        default=None,
        max_length=9,
        description="Unterstützte SEPA-Datenformate",
    )


class ScheduledBatchDebitParameter1(FinTSDataElementGroup):
    """Parameter terminierte SEPA-Sammellastschrift, version 1.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    min_advance_notice_FNAL_RCUR: FinTSNumeric = Field(
        ge=0,
        lt=10000,
        description="Minimale Vorlaufzeit FNAL/RCUR (Tage)",
    )
    max_advance_notice_FNAL_RCUR: FinTSNumeric = Field(
        ge=0,
        lt=10000,
        description="Maximale Vorlaufzeit FNAL/RCUR (Tage)",
    )
    min_advance_notice_FRST_OOFF: FinTSNumeric = Field(
        ge=0,
        lt=10000,
        description="Minimale Vorlaufzeit FRST/OOFF (Tage)",
    )
    max_advance_notice_FRST_OOFF: FinTSNumeric = Field(
        ge=0,
        lt=10000,
        description="Maximale Vorlaufzeit FRST/OOFF (Tage)",
    )
    max_debit_count: FinTSNumeric = Field(
        ge=0,
        lt=10000000,
        description="Maximale Anzahl DirectDebitTransfer TransactionInformation",
    )
    sum_amount_required: FinTSBool = Field(
        description="Summenfeld benötigt",
    )
    single_booking_allowed: FinTSBool = Field(
        description="Einzelbuchung erlaubt",
    )


class ScheduledBatchDebitParameter2(FinTSDataElementGroup):
    """Parameter terminierte SEPA-Sammellastschrift, version 2.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    min_advance_notice: FinTSAlphanumeric = Field(
        max_length=99,
        description="Minimale Vorlaufzeit SEPA-Lastschrift",
    )
    max_advance_notice: FinTSAlphanumeric = Field(
        max_length=99,
        description="Maximale Vorlaufzeit SEPA-Lastschrift",
    )
    max_debit_count: FinTSNumeric = Field(
        ge=0,
        lt=10000000,
        description="Maximale Anzahl DirectDebitTransfer TransactionInformation",
    )
    sum_amount_required: FinTSBool = Field(
        description="Summenfeld benötigt",
    )
    single_booking_allowed: FinTSBool = Field(
        description="Einzelbuchung erlaubt",
    )
    allowed_purpose_codes: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=4096,
        description="Zulässige purpose codes",
    )
    supported_sepa_formats: list[FinTSAlphanumeric] | None = Field(
        default=None,
        max_length=9,
        description="Unterstützte SEPA-Datenformate",
    )


# =============================================================================
# Query Parameter DEGs
# =============================================================================


class QueryScheduledDebitParameter1(FinTSDataElementGroup):
    """Parameter Bestand terminierter SEPA-Einzellastschriften, version 1.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    date_range_allowed: FinTSBool = Field(
        description="Zeitraum möglich",
    )
    max_number_responses_allowed: FinTSBool = Field(
        description="Eingabe Anzahl Einträge erlaubt",
    )


class QueryScheduledDebitParameter2(FinTSDataElementGroup):
    """Parameter Bestand terminierter SEPA-Einzellastschriften, version 2.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    max_number_responses_allowed: FinTSBool = Field(
        description="Eingabe Anzahl Einträge erlaubt",
    )
    date_range_allowed: FinTSBool = Field(
        description="Zeitraum möglich",
    )
    supported_sepa_formats: list[FinTSAlphanumeric] | None = Field(
        default=None,
        max_length=9,
        description="Unterstützte SEPA-Datenformate",
    )


__all__ = [
    # CAMT/Statement
    "SupportedMessageTypes",
    "BookedCamtStatements",
    "SupportedSEPAPainMessages",
    # Transfer
    "BatchTransferParameter",
    # Debit
    "ScheduledDebitParameter1",
    "ScheduledDebitParameter2",
    "ScheduledBatchDebitParameter1",
    "ScheduledBatchDebitParameter2",
    # Query
    "QueryScheduledDebitParameter1",
    "QueryScheduledDebitParameter2",
]

