"""FinTS TAN-related Data Element Groups (DEGs) for PIN/TAN procedures."""

from __future__ import annotations

from pydantic import Field

from ..base import FinTSDataElementGroup
from ..types import (
    FinTSAlphanumeric,
    FinTSBinary,
    FinTSDate,
    FinTSID,
    FinTSNumeric,
    FinTSTime,
)
from .enums import (
    TANMediaClass,
    TANMediumStatus,
)
from .identifiers import (
    AccountIdentifier,
    AccountInternational,
)

# =============================================================================
# TAN Media DEGs
# =============================================================================


class TANMediaBase(FinTSDataElementGroup):
    """Base class for TAN media information."""

    tan_medium_class: TANMediaClass = Field(
        description="TAN-Medium-Klasse",
    )
    status: TANMediumStatus = Field(
        description="Status des TAN-Mediums",
    )
    card_number: FinTSID | None = Field(
        default=None,
        description="Kartennummer",
    )
    card_sequence: FinTSID | None = Field(
        default=None,
        description="Kartenfolgenummer",
    )
    card_type: FinTSNumeric | None = Field(
        default=None,
        description="Kartenart",
    )
    account: AccountIdentifier | None = Field(
        default=None,
        description="Kontonummer Auftraggeber",
    )
    valid_from: FinTSDate | None = Field(
        default=None,
        description="Gültig ab",
    )
    valid_until: FinTSDate | None = Field(
        default=None,
        description="Gültig bis",
    )
    tan_list_number: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=20,
        description="TAN-Listennummer",
    )
    tan_medium_name: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=32,
        description="Bezeichnung des TAN-Mediums",
    )
    mobile_number_masked: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=35,
        description="Mobiltelefonnummer, verschleiert",
    )
    mobile_number: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=35,
        description="Mobiltelefonnummer",
    )
    sms_charge_account: AccountInternational | None = Field(
        default=None,
        description="SMS-Abbuchungskonto",
    )
    number_free_tans: FinTSNumeric | None = Field(
        default=None,
        ge=0,
        lt=1000,
        description="Anzahl freie TANs",
    )
    last_use: FinTSDate | None = Field(
        default=None,
        description="Letzte Benutzung",
    )
    active_since: FinTSDate | None = Field(
        default=None,
        description="Freigeschaltet am",
    )


class TANMedia4(TANMediaBase):
    """TAN-Medium-Liste, version 4."""

    pass


class TANMedia5(TANMediaBase):
    """TAN-Medium-Liste, version 5 (adds security_function)."""

    security_function: FinTSNumeric | None = Field(
        default=None,
        description="Sicherheitsfunktion, kodiert",
    )


class ChallengeValidUntil(FinTSDataElementGroup):
    """Gültigkeitsdatum und -uhrzeit für Challenge."""

    date: FinTSDate = Field(
        description="Datum",
    )
    time: FinTSTime = Field(
        description="Uhrzeit",
    )


class ParameterChallengeClass(FinTSDataElementGroup):
    """Parameter Challenge-Klasse (up to 9 class parameters)."""

    parameters: list[FinTSAlphanumeric] | None = Field(
        default=None,
        max_length=9,
        description="Challenge-Klassen-Parameter",
    )


class ResponseHHDUC(FinTSDataElementGroup):
    """Antwort HHD_UC (Chipkarten-Antwort) - chip card TAN generator response data."""

    atc: FinTSAlphanumeric = Field(
        max_length=5,
        description="ATC (Application Transaction Counter)",
    )
    ac: FinTSBinary = Field(
        description="Application Cryptogram AC",
    )
    ef_id_data: FinTSBinary = Field(
        description="EF_ID Data",
    )
    cvr: FinTSBinary = Field(
        description="CVR (Card Verification Results)",
    )
    version_info_chiptan: FinTSBinary = Field(
        description="Versionsinfo der chipTAN-Applikation",
    )


__all__ = [
    "TANMediaBase",
    "TANMedia4",
    "TANMedia5",
    "ChallengeValidUntil",
    "ParameterChallengeClass",
    "ResponseHHDUC",
]
