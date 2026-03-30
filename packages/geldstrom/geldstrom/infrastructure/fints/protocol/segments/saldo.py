"""FinTS Balance Segments (Saldenabfrage/-rückmeldung).

Request segments (HKSAL) query account balances.
Response segments (HISAL) contain balance information.
"""
from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from ..base import FinTSSegment
from ..formals import (
    AccountIdentifier,
    AccountInternational,
    Amount,
    Balance,
    BalanceSimple,
    Timestamp,
)
from ..types import (
    FinTSAlphanumeric,
    FinTSBool,
    FinTSCurrency,
    FinTSDate,
    FinTSNumeric,
    FinTSTime,
)

# =============================================================================
# Balance Request Segments (HKSAL)
# =============================================================================

# Note: Field order is critical in FinTS! The `account` field MUST come before
# `all_accounts` in the wire format. We cannot use inheritance for common fields
# because Pydantic puts parent class fields first.


class HKSAL5(FinTSSegment):
    """Saldenabfrage, version 5.

    Request account balances using Account2 format.

    Source: HBCI Homebanking-Computer-Interface, Schnittstellenspezifikation
    """

    SEGMENT_TYPE: ClassVar[str] = "HKSAL"
    SEGMENT_VERSION: ClassVar[int] = 5

    account: AccountIdentifier = Field(
        description="Kontoverbindung Auftraggeber",
    )
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


class HKSAL6(FinTSSegment):
    """Saldenabfrage, version 6.

    Request account balances using Account3 format.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    SEGMENT_TYPE: ClassVar[str] = "HKSAL"
    SEGMENT_VERSION: ClassVar[int] = 6

    account: AccountIdentifier = Field(
        description="Kontoverbindung Auftraggeber",
    )
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


class HKSAL7(FinTSSegment):
    """Saldenabfrage, version 7.

    Request account balances using international account format (KTI1).

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    SEGMENT_TYPE: ClassVar[str] = "HKSAL"
    SEGMENT_VERSION: ClassVar[int] = 7

    account: AccountInternational = Field(
        description="Kontoverbindung international",
    )
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


# Type alias for backwards compatibility
HKSALBase = HKSAL5  # Base class alias


# Version registry for HKSAL
HKSAL_VERSIONS: dict[int, type[HKSALBase]] = {
    5: HKSAL5,
    6: HKSAL6,
    7: HKSAL7,
}


# =============================================================================
# Balance Response Segments (HISAL)
# =============================================================================

# Note: Field order is critical in FinTS! We must match the wire format order.


class HISAL5(FinTSSegment):
    """Saldenrückmeldung, version 5.

    Balance response using Account2 format and Balance1 (simple balance).

    Source: HBCI Homebanking-Computer-Interface, Schnittstellenspezifikation
    """

    SEGMENT_TYPE: ClassVar[str] = "HISAL"
    SEGMENT_VERSION: ClassVar[int] = 5

    account: AccountIdentifier = Field(
        description="Kontoverbindung Auftraggeber",
    )
    account_product: FinTSAlphanumeric = Field(
        max_length=30,
        description="Kontoproduktbezeichnung",
    )
    currency: FinTSCurrency = Field(
        description="Kontowährung",
    )
    balance_booked: BalanceSimple = Field(
        description="Gebuchter Saldo",
    )
    balance_pending: BalanceSimple | None = Field(
        default=None,
        description="Saldo der vorgemerkten Umsätze",
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
    booking_date: FinTSDate | None = Field(
        default=None,
        description="Buchungsdatum des Saldos",
    )
    booking_time: FinTSTime | None = Field(
        default=None,
        description="Buchungsuhrzeit des Saldos",
    )


class HISAL6(FinTSSegment):
    """Saldenrückmeldung, version 6.

    Balance response using Account3 format and Balance2 (nested amount).

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    SEGMENT_TYPE: ClassVar[str] = "HISAL"
    SEGMENT_VERSION: ClassVar[int] = 6

    account: AccountIdentifier = Field(
        description="Kontoverbindung Auftraggeber",
    )
    account_product: FinTSAlphanumeric = Field(
        max_length=30,
        description="Kontoproduktbezeichnung",
    )
    currency: FinTSCurrency = Field(
        description="Kontowährung",
    )
    balance_booked: Balance = Field(
        description="Gebuchter Saldo",
    )
    balance_pending: Balance | None = Field(
        default=None,
        description="Saldo der vorgemerkten Umsätze",
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
    overdraft: Amount | None = Field(
        default=None,
        description="Überziehung",
    )
    booking_timestamp: Timestamp | None = Field(
        default=None,
        description="Buchungszeitpunkt",
    )
    date_due: FinTSDate | None = Field(
        default=None,
        description="Fälligkeit",
    )


class HISAL7(FinTSSegment):
    """Saldenrückmeldung, version 7.

    Balance response using international account format (KTI1).

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    SEGMENT_TYPE: ClassVar[str] = "HISAL"
    SEGMENT_VERSION: ClassVar[int] = 7

    account: AccountInternational = Field(
        description="Kontoverbindung international",
    )
    account_product: FinTSAlphanumeric = Field(
        max_length=30,
        description="Kontoproduktbezeichnung",
    )
    currency: FinTSCurrency = Field(
        description="Kontowährung",
    )
    balance_booked: Balance = Field(
        description="Gebuchter Saldo",
    )
    balance_pending: Balance | None = Field(
        default=None,
        description="Saldo der vorgemerkten Umsätze",
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
    overdraft: Amount | None = Field(
        default=None,
        description="Überziehung",
    )
    booking_timestamp: Timestamp | None = Field(
        default=None,
        description="Buchungszeitpunkt",
    )
    date_due: FinTSDate | None = Field(
        default=None,
        description="Fälligkeit",
    )


# Type alias for backwards compatibility
HISALBase = HISAL5  # Base class alias


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
    "HKSAL5",
    "HKSAL6",
    "HKSAL7",
    "HKSALBase",  # Type alias for HKSAL5 (backwards compatibility)
    # Response segments
    "HISAL5",
    "HISAL6",
    "HISAL7",
    "HISALBase",  # Type alias for HISAL5 (backwards compatibility)
    # Registries
    "HKSAL_VERSIONS",
    "HISAL_VERSIONS",
    # Helpers
    "get_hksal_class",
    "get_hisal_class",
]

