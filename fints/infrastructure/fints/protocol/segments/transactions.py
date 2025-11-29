"""FinTS Transaction Segments (Kontoumsätze).

Request segments (HKKAZ, HKCAZ) query account transactions.
Response segments (HIKAZ, HICAZ) contain transaction data.

HKKAZ/HIKAZ: MT940 format (legacy)
HKCAZ/HICAZ: CAMT XML format (modern)
"""
from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from ..base import FinTSSegment
from ..types import (
    FinTSAlphanumeric,
    FinTSBinary,
    FinTSBool,
    FinTSDate,
    FinTSNumeric,
)
from ..formals import (
    AccountIdentifier,
    AccountInternational,
)


# =============================================================================
# MT940 Transaction Request Segments (HKKAZ)
# =============================================================================


class HKKAZBase(FinTSSegment):
    """Base class for MT940 transaction request segments."""

    SEGMENT_TYPE: ClassVar[str] = "HKKAZ"

    all_accounts: FinTSBool = Field(
        description="Alle Konten abfragen",
    )
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
        description="Aufsetzpunkt für Fortsetzung",
    )


class HKKAZ5(HKKAZBase):
    """Kontoumsätze anfordern/Zeitraum, version 5.

    Request MT940 transactions using Account2 format.

    Source: HBCI Homebanking-Computer-Interface, Schnittstellenspezifikation
    """

    SEGMENT_VERSION: ClassVar[int] = 5

    account: AccountIdentifier = Field(
        description="Kontoverbindung Auftraggeber",
    )


class HKKAZ6(HKKAZBase):
    """Kontoumsätze anfordern/Zeitraum, version 6.

    Request MT940 transactions using Account3 format.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    SEGMENT_VERSION: ClassVar[int] = 6

    account: AccountIdentifier = Field(
        description="Kontoverbindung Auftraggeber",
    )


class HKKAZ7(HKKAZBase):
    """Kontoumsätze anfordern/Zeitraum, version 7.

    Request MT940 transactions using international account format.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    SEGMENT_VERSION: ClassVar[int] = 7

    account: AccountInternational = Field(
        description="Kontoverbindung international",
    )


HKKAZ_VERSIONS: dict[int, type[HKKAZBase]] = {
    5: HKKAZ5,
    6: HKKAZ6,
    7: HKKAZ7,
}


# =============================================================================
# MT940 Transaction Response Segments (HIKAZ)
# =============================================================================


class HIKAZBase(FinTSSegment):
    """Base class for MT940 transaction response segments."""

    SEGMENT_TYPE: ClassVar[str] = "HIKAZ"

    statement_booked: FinTSBinary = Field(
        description="Gebuchte Umsätze (MT940 format)",
    )
    statement_pending: FinTSBinary | None = Field(
        default=None,
        description="Nicht gebuchte Umsätze (MT942 format)",
    )


class HIKAZ5(HIKAZBase):
    """Kontoumsätze rückmelden/Zeitraum, version 5.

    Source: HBCI Homebanking-Computer-Interface, Schnittstellenspezifikation
    """

    SEGMENT_VERSION: ClassVar[int] = 5


class HIKAZ6(HIKAZBase):
    """Kontoumsätze rückmelden/Zeitraum, version 6.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    SEGMENT_VERSION: ClassVar[int] = 6


class HIKAZ7(HIKAZBase):
    """Kontoumsätze rückmelden/Zeitraum, version 7.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    SEGMENT_VERSION: ClassVar[int] = 7


HIKAZ_VERSIONS: dict[int, type[HIKAZBase]] = {
    5: HIKAZ5,
    6: HIKAZ6,
    7: HIKAZ7,
}


# =============================================================================
# CAMT Transaction Request Segments (HKCAZ)
# =============================================================================


class HKCAZ1(FinTSSegment):
    """Kontoumsätze anfordern/Zeitraum (CAMT), version 1.

    Request transactions in CAMT XML format.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    SEGMENT_TYPE: ClassVar[str] = "HKCAZ"
    SEGMENT_VERSION: ClassVar[int] = 1

    account: AccountInternational = Field(
        description="Kontoverbindung international",
    )
    supported_camt_messages: list[FinTSAlphanumeric] = Field(
        max_length=99,
        description="Unterstützte camt-messages",
    )
    all_accounts: FinTSBool = Field(
        description="Alle Konten abfragen",
    )
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
        description="Aufsetzpunkt für Fortsetzung",
    )


HKCAZ_VERSIONS: dict[int, type[FinTSSegment]] = {
    1: HKCAZ1,
}


# =============================================================================
# CAMT Transaction Response Segments (HICAZ)
# =============================================================================


class HICAZ1(FinTSSegment):
    """Kontoumsätze rückmelden/Zeitraum (CAMT), version 1.

    Response containing transactions in CAMT XML format.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    SEGMENT_TYPE: ClassVar[str] = "HICAZ"
    SEGMENT_VERSION: ClassVar[int] = 1

    account: AccountInternational = Field(
        description="Kontoverbindung Auftraggeber",
    )
    camt_descriptor: FinTSAlphanumeric = Field(
        description="camt-Deskriptor (e.g., urn:iso:std:iso:20022:tech:xsd:camt.052.001.02)",
    )
    statement_booked: list[FinTSBinary] = Field(
        min_length=1,
        description="Gebuchte Umsätze (CAMT XML)",
    )
    statement_pending: FinTSBinary | None = Field(
        default=None,
        description="Nicht gebuchte Umsätze",
    )


HICAZ_VERSIONS: dict[int, type[FinTSSegment]] = {
    1: HICAZ1,
}


__all__ = [
    # MT940 Request
    "HKKAZBase",
    "HKKAZ5",
    "HKKAZ6",
    "HKKAZ7",
    "HKKAZ_VERSIONS",
    # MT940 Response
    "HIKAZBase",
    "HIKAZ5",
    "HIKAZ6",
    "HIKAZ7",
    "HIKAZ_VERSIONS",
    # CAMT Request
    "HKCAZ1",
    "HKCAZ_VERSIONS",
    # CAMT Response
    "HICAZ1",
    "HICAZ_VERSIONS",
]

