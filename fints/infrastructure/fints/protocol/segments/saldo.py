"""FinTS Balance Segments (Saldenabfrage/-rückmeldung).

Request segments (HKSAL) query account balances.
Response segments (HISAL) contain balance information.
"""
from __future__ import annotations

from datetime import date, time
from typing import ClassVar

from pydantic import Field

from ..base import FinTSSegment
from ..types import FinTSAlphanumeric, FinTSBool, FinTSCurrency, FinTSDate, FinTSNumeric, FinTSTime
from ..formals import (
    AccountIdentifier,
    AccountInternational,
    Amount,
    Balance,
    BalanceSimple,
    Timestamp,
)


# =============================================================================
# Balance Request Segments (HKSAL)
# =============================================================================


class HKSALBase(FinTSSegment):
    """Base class for balance request segments."""

    SEGMENT_TYPE: ClassVar[str] = "HKSAL"

    all_accounts: FinTSBool = Field(
        description="Alle Konten abfragen",
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


class HKSAL5(HKSALBase):
    """Saldenabfrage, version 5.

    Request account balances using Account2 format.

    Source: HBCI Homebanking-Computer-Interface, Schnittstellenspezifikation
    """

    SEGMENT_VERSION: ClassVar[int] = 5

    account: AccountIdentifier = Field(
        description="Kontoverbindung Auftraggeber",
    )


class HKSAL6(HKSALBase):
    """Saldenabfrage, version 6.

    Request account balances using Account3 format.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    SEGMENT_VERSION: ClassVar[int] = 6

    account: AccountIdentifier = Field(
        description="Kontoverbindung Auftraggeber",
    )


class HKSAL7(HKSALBase):
    """Saldenabfrage, version 7.

    Request account balances using international account format (KTI1).

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    SEGMENT_VERSION: ClassVar[int] = 7

    account: AccountInternational = Field(
        description="Kontoverbindung international",
    )


# Version registry for HKSAL
HKSAL_VERSIONS: dict[int, type[HKSALBase]] = {
    5: HKSAL5,
    6: HKSAL6,
    7: HKSAL7,
}


# =============================================================================
# Balance Response Segments (HISAL)
# =============================================================================


class HISALBase(FinTSSegment):
    """Base class for balance response segments."""

    SEGMENT_TYPE: ClassVar[str] = "HISAL"

    account_product: FinTSAlphanumeric = Field(
        max_length=30,
        description="Kontoproduktbezeichnung",
    )
    currency: FinTSCurrency = Field(
        description="Kontowährung",
    )
    line_of_credit: Amount | None = Field(
        default=None,
        description="Kreditlinie",
    )
    available_amount: Amount | None = Field(
        default=None,
        description="Verfügbarer Betrag",
    )
    used_amount: Amount | None = Field(
        default=None,
        description="Bereits verfügter Betrag",
    )
    date_due: FinTSDate | None = Field(
        default=None,
        description="Fälligkeit",
    )


class HISAL5(HISALBase):
    """Saldenrückmeldung, version 5.

    Balance response using Account2 format and Balance1 (simple balance).

    Source: HBCI Homebanking-Computer-Interface, Schnittstellenspezifikation
    """

    SEGMENT_VERSION: ClassVar[int] = 5

    account: AccountIdentifier = Field(
        description="Kontoverbindung Auftraggeber",
    )
    balance_booked: BalanceSimple = Field(
        description="Gebuchter Saldo",
    )
    balance_pending: BalanceSimple | None = Field(
        default=None,
        description="Saldo der vorgemerkten Umsätze",
    )
    booking_date: FinTSDate | None = Field(
        default=None,
        description="Buchungsdatum des Saldos",
    )
    booking_time: FinTSTime | None = Field(
        default=None,
        description="Buchungsuhrzeit des Saldos",
    )


class HISAL6(HISALBase):
    """Saldenrückmeldung, version 6.

    Balance response using Account3 format and Balance2 (nested amount).

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    SEGMENT_VERSION: ClassVar[int] = 6

    account: AccountIdentifier = Field(
        description="Kontoverbindung Auftraggeber",
    )
    balance_booked: Balance = Field(
        description="Gebuchter Saldo",
    )
    balance_pending: Balance | None = Field(
        default=None,
        description="Saldo der vorgemerkten Umsätze",
    )
    overdraft: Amount | None = Field(
        default=None,
        description="Überziehung",
    )
    booking_timestamp: Timestamp | None = Field(
        default=None,
        description="Buchungszeitpunkt",
    )


class HISAL7(HISALBase):
    """Saldenrückmeldung, version 7.

    Balance response using international account format (KTI1).

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    SEGMENT_VERSION: ClassVar[int] = 7

    account: AccountInternational = Field(
        description="Kontoverbindung international",
    )
    balance_booked: Balance = Field(
        description="Gebuchter Saldo",
    )
    balance_pending: Balance | None = Field(
        default=None,
        description="Saldo der vorgemerkten Umsätze",
    )
    overdraft: Amount | None = Field(
        default=None,
        description="Überziehung",
    )
    booking_timestamp: Timestamp | None = Field(
        default=None,
        description="Buchungszeitpunkt",
    )


# Version registry for HISAL
HISAL_VERSIONS: dict[int, type[HISALBase]] = {
    5: HISAL5,
    6: HISAL6,
    7: HISAL7,
}


def get_hksal_class(version: int) -> type[HKSALBase]:
    """Get HKSAL class for version.

    Args:
        version: Segment version number

    Returns:
        HKSAL class for the version

    Raises:
        KeyError: If version not supported
    """
    return HKSAL_VERSIONS[version]


def get_hisal_class(version: int) -> type[HISALBase]:
    """Get HISAL class for version.

    Args:
        version: Segment version number

    Returns:
        HISAL class for the version

    Raises:
        KeyError: If version not supported
    """
    return HISAL_VERSIONS[version]


__all__ = [
    # Request segments
    "HKSALBase",
    "HKSAL5",
    "HKSAL6",
    "HKSAL7",
    # Response segments
    "HISALBase",
    "HISAL5",
    "HISAL6",
    "HISAL7",
    # Registries
    "HKSAL_VERSIONS",
    "HISAL_VERSIONS",
    # Helpers
    "get_hksal_class",
    "get_hisal_class",
]

