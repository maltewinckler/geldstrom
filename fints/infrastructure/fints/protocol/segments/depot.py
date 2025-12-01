"""FinTS Depot (Securities) Segments.

These segments handle securities/depot information:
- Portfolio requests (HKWPD)
- Portfolio responses (HIWPD)
"""
from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from ..base import FinTSSegment, FinTSDataElementGroup
from ..types import (
    FinTSAlphanumeric,
    FinTSBinary,
    FinTSCode,
    FinTSCurrency,
    FinTSNumeric,
)
from ..formals import (
    AccountIdentifier,
    BankIdentifier,
)


# =============================================================================
# Depot Account DEGs
# =============================================================================


class DepotAccount2(FinTSDataElementGroup):
    """Depot account for version 5 (Account2 compatible).

    Uses country identifier and bank code directly.
    """

    account_number: FinTSAlphanumeric = Field(
        description="Konto-/Depotnummer",
    )
    subaccount_number: FinTSAlphanumeric = Field(
        description="Unterkontomerkmal",
    )
    country_identifier: FinTSAlphanumeric = Field(
        description="Länderkennzeichen",
    )
    bank_code: FinTSAlphanumeric = Field(
        max_length=30,
        description="Kreditinstitutscode",
    )


class DepotAccount3(FinTSDataElementGroup):
    """Depot account for version 6 (Account3 compatible).

    Uses BankIdentifier DEG.
    """

    account_number: FinTSAlphanumeric = Field(
        description="Konto-/Depotnummer",
    )
    subaccount_number: FinTSAlphanumeric = Field(
        description="Unterkontomerkmal",
    )
    bank_identifier: BankIdentifier = Field(
        description="Kreditinstitutskennung",
    )


# =============================================================================
# Depot Request Segments
# =============================================================================


class HKWPD5(FinTSSegment):
    """Depotaufstellung anfordern (Request Portfolio), version 5.

    Requests securities portfolio information.

    Source: HBCI Schnittstellenspezifikation
    """

    SEGMENT_TYPE: ClassVar[str] = "HKWPD"
    SEGMENT_VERSION: ClassVar[int] = 5

    account: DepotAccount2 = Field(
        description="Depot",
    )
    currency: FinTSCurrency | None = Field(
        default=None,
        description="Währung der Depotaufstellung",
    )
    quality: FinTSNumeric | None = Field(
        default=None,
        ge=0,
        lt=10,
        description="Kursqualität",
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


class HKWPD6(FinTSSegment):
    """Depotaufstellung anfordern (Request Portfolio), version 6.

    Requests securities portfolio information.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    SEGMENT_TYPE: ClassVar[str] = "HKWPD"
    SEGMENT_VERSION: ClassVar[int] = 6

    account: DepotAccount3 = Field(
        description="Depot",
    )
    currency: FinTSCurrency | None = Field(
        default=None,
        description="Währung der Depotaufstellung",
    )
    quality: FinTSCode | None = Field(
        default=None,
        description="Kursqualität",
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
# Depot Response Segments
# =============================================================================


class HIWPD5(FinTSSegment):
    """Depotaufstellung rückmelden (Portfolio Response), version 5.

    Returns securities portfolio information.

    Source: HBCI Schnittstellenspezifikation
    """

    SEGMENT_TYPE: ClassVar[str] = "HIWPD"
    SEGMENT_VERSION: ClassVar[int] = 5

    holdings: FinTSBinary = Field(
        description="Depotaufstellung (MT535 or similar)",
    )


class HIWPD6(FinTSSegment):
    """Depotaufstellung rückmelden (Portfolio Response), version 6.

    Returns securities portfolio information.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    SEGMENT_TYPE: ClassVar[str] = "HIWPD"
    SEGMENT_VERSION: ClassVar[int] = 6

    holdings: FinTSBinary = Field(
        description="Depotaufstellung (MT535 or similar)",
    )


# =============================================================================
# Version Registries
# =============================================================================


HKWPD_VERSIONS: dict[int, type[FinTSSegment]] = {
    5: HKWPD5,
    6: HKWPD6,
}

HIWPD_VERSIONS: dict[int, type[FinTSSegment]] = {
    5: HIWPD5,
    6: HIWPD6,
}


__all__ = [
    # DEGs
    "DepotAccount2",
    "DepotAccount3",
    # Request
    "HKWPD5",
    "HKWPD6",
    "HKWPD_VERSIONS",
    # Response
    "HIWPD5",
    "HIWPD6",
    "HIWPD_VERSIONS",
]

