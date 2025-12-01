"""FinTS Authentication Segments.

These segments handle authentication including:
- Identification (HKIDN)
- Processing preparation (HKVVB)
- TAN handling (HKTAN, HITAN)
- TAN media (HKTAB, HITAB)
"""
from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from ..base import FinTSSegment
from ..types import (
    FinTSAlphanumeric,
    FinTSBinary,
    FinTSBool,
    FinTSCode,
    FinTSNumeric,
)
from ..formals import (
    AccountInternational,
    BankIdentifier,
    ChallengeValidUntil,
    Language,
    ParameterChallengeClass,
    ResponseHHDUC,
    SystemIDStatus,
    TANMedia4,
    TANMedia5,
    TANMediaClass,
    TANMediaType,
    TANUsageOption,
)


# =============================================================================
# Identification Segment
# =============================================================================


class HKIDN2(FinTSSegment):
    """Identifikation (Identification), version 2.

    Identifies the customer and system to the bank.

    Source: FinTS 3.0 Formals
    """

    SEGMENT_TYPE: ClassVar[str] = "HKIDN"
    SEGMENT_VERSION: ClassVar[int] = 2

    bank_identifier: BankIdentifier = Field(
        description="Kreditinstitutskennung",
    )
    customer_id: FinTSAlphanumeric = Field(
        description="Kunden-ID",
    )
    system_id: FinTSAlphanumeric = Field(
        description="Kundensystem-ID",
    )
    system_id_status: SystemIDStatus = Field(
        description="Kundensystem-Status",
    )


# =============================================================================
# Processing Preparation Segment
# =============================================================================


class HKVVB3(FinTSSegment):
    """Verarbeitungsvorbereitung (Processing Preparation), version 3.

    Sets up the dialog with version and language info.

    Source: FinTS 3.0 Formals
    """

    SEGMENT_TYPE: ClassVar[str] = "HKVVB"
    SEGMENT_VERSION: ClassVar[int] = 3

    bpd_version: FinTSNumeric = Field(
        ge=0,
        lt=1000,
        description="BPD-Version",
    )
    upd_version: FinTSNumeric = Field(
        ge=0,
        lt=1000,
        description="UPD-Version",
    )
    language: Language = Field(
        description="Dialogsprache",
    )
    product_name: FinTSAlphanumeric = Field(
        max_length=25,
        description="Produktbezeichnung",
    )
    product_version: FinTSAlphanumeric = Field(
        max_length=5,
        description="Produktversion",
    )


# =============================================================================
# TAN Request Segments (HKTAN)
# =============================================================================


class HKTANBase(FinTSSegment):
    """Base class for TAN request segments."""

    SEGMENT_TYPE: ClassVar[str] = "HKTAN"

    tan_process: FinTSCode = Field(
        description="TAN-Prozess (1=Einschritt, 2=Erste Hälfte, 3=Zweite Hälfte, 4=Prozess stornieren, S=Decoupled)",
    )


class HKTAN2(HKTANBase):
    """Zwei-Schritt-TAN-Einreichung, version 2.

    Source: FinTS 3.0 Sicherheitsverfahren PIN/TAN
    """

    SEGMENT_VERSION: ClassVar[int] = 2

    task_hash_value: FinTSBinary | None = Field(
        default=None,
        description="Auftrags-Hashwert",
    )
    task_reference: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=35,
        description="Auftragsreferenz",
    )
    tan_list_number: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=20,
        description="TAN-Listennummer",
    )
    further_tan_follows: FinTSBool | None = Field(
        default=None,
        description="Weitere TAN folgt",
    )
    cancel_task: FinTSBool | None = Field(
        default=None,
        description="Auftrag stornieren",
    )
    challenge_class: FinTSNumeric | None = Field(
        default=None,
        ge=0,
        lt=100,
        description="Challenge-Klasse",
    )
    parameter_challenge_class: ParameterChallengeClass | None = Field(
        default=None,
        description="Parameter Challenge-Klasse",
    )


class HKTAN6(HKTANBase):
    """Zwei-Schritt-TAN-Einreichung, version 6.

    Source: FinTS 3.0 Sicherheitsverfahren PIN/TAN
    """

    SEGMENT_VERSION: ClassVar[int] = 6

    segment_type: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=6,
        description="Segmentkennung",
    )
    account: AccountInternational | None = Field(
        default=None,
        description="Kontoverbindung international Auftraggeber",
    )
    task_hash_value: FinTSBinary | None = Field(
        default=None,
        description="Auftrags-Hashwert",
    )
    task_reference: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=35,
        description="Auftragsreferenz",
    )
    further_tan_follows: FinTSBool | None = Field(
        default=None,
        description="Weitere TAN folgt",
    )
    cancel_task: FinTSBool | None = Field(
        default=None,
        description="Auftrag stornieren",
    )
    sms_charge_account: AccountInternational | None = Field(
        default=None,
        description="SMS-Abbuchungskonto",
    )
    challenge_class: FinTSNumeric | None = Field(
        default=None,
        ge=0,
        lt=100,
        description="Challenge-Klasse",
    )
    parameter_challenge_class: ParameterChallengeClass | None = Field(
        default=None,
        description="Parameter Challenge-Klasse",
    )
    tan_medium_name: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=32,
        description="Bezeichnung des TAN-Mediums",
    )
    response_hhd_uc: ResponseHHDUC | None = Field(
        default=None,
        description="Antwort HHD_UC",
    )


class HKTAN7(HKTANBase):
    """Zwei-Schritt-TAN-Einreichung, version 7.

    Source: FinTS 3.0 Sicherheitsverfahren PIN/TAN
    """

    SEGMENT_VERSION: ClassVar[int] = 7

    segment_type: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=6,
        description="Segmentkennung",
    )
    account: AccountInternational | None = Field(
        default=None,
        description="Kontoverbindung international Auftraggeber",
    )
    task_hash_value: FinTSBinary | None = Field(
        default=None,
        description="Auftrags-Hashwert",
    )
    task_reference: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=35,
        description="Auftragsreferenz",
    )
    further_tan_follows: FinTSBool | None = Field(
        default=None,
        description="Weitere TAN folgt",
    )
    cancel_task: FinTSBool | None = Field(
        default=None,
        description="Auftrag stornieren",
    )
    sms_charge_account: AccountInternational | None = Field(
        default=None,
        description="SMS-Abbuchungskonto",
    )
    challenge_class: FinTSNumeric | None = Field(
        default=None,
        ge=0,
        lt=100,
        description="Challenge-Klasse",
    )
    parameter_challenge_class: ParameterChallengeClass | None = Field(
        default=None,
        description="Parameter Challenge-Klasse",
    )
    tan_medium_name: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=32,
        description="Bezeichnung des TAN-Mediums",
    )
    response_hhd_uc: ResponseHHDUC | None = Field(
        default=None,
        description="Antwort HHD_UC",
    )


# =============================================================================
# TAN Response Segments (HITAN)
# =============================================================================


class HITANBase(FinTSSegment):
    """Base class for TAN response segments."""

    SEGMENT_TYPE: ClassVar[str] = "HITAN"

    tan_process: FinTSCode = Field(
        description="TAN-Prozess",
    )
    task_hash_value: FinTSBinary | None = Field(
        default=None,
        description="Auftrags-Hashwert",
    )
    task_reference: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=35,
        description="Auftragsreferenz",
    )
    challenge: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=2048,
        description="Challenge",
    )


class HITAN6(HITANBase):
    """Zwei-Schritt-TAN-Einreichung Rückmeldung, version 6.

    Source: FinTS 3.0 Sicherheitsverfahren PIN/TAN
    """

    SEGMENT_VERSION: ClassVar[int] = 6

    challenge_hhduc: FinTSBinary | None = Field(
        default=None,
        description="Challenge HHD_UC",
    )
    challenge_valid_until: ChallengeValidUntil | None = Field(
        default=None,
        description="Gültigkeitsdatum und -uhrzeit für Challenge",
    )
    tan_medium_name: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=32,
        description="Bezeichnung des TAN-Mediums",
    )


class HITAN7(HITANBase):
    """Zwei-Schritt-TAN-Einreichung Rückmeldung, version 7.

    Source: FinTS 3.0 Sicherheitsverfahren PIN/TAN
    """

    SEGMENT_VERSION: ClassVar[int] = 7

    challenge_hhduc: FinTSBinary | None = Field(
        default=None,
        description="Challenge HHD_UC",
    )
    challenge_valid_until: ChallengeValidUntil | None = Field(
        default=None,
        description="Gültigkeitsdatum und -uhrzeit für Challenge",
    )
    tan_medium_name: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=32,
        description="Bezeichnung des TAN-Mediums",
    )


# =============================================================================
# TAN Media Segments
# =============================================================================


class HKTAB4(FinTSSegment):
    """TAN-Generator/Liste anzeigen Bestand, version 4.

    Request TAN media list.

    Source: FinTS 3.0 Sicherheitsverfahren PIN/TAN
    """

    SEGMENT_TYPE: ClassVar[str] = "HKTAB"
    SEGMENT_VERSION: ClassVar[int] = 4

    tan_media_type: TANMediaType = Field(
        description="TAN-Medium-Art",
    )
    tan_media_class: TANMediaClass = Field(
        description="TAN-Medium-Klasse",
    )


class HKTAB5(FinTSSegment):
    """TAN-Generator/Liste anzeigen Bestand, version 5.

    Request TAN media list.

    Source: FinTS 3.0 Sicherheitsverfahren PIN/TAN
    """

    SEGMENT_TYPE: ClassVar[str] = "HKTAB"
    SEGMENT_VERSION: ClassVar[int] = 5

    tan_media_type: TANMediaType = Field(
        description="TAN-Medium-Art",
    )
    tan_media_class: TANMediaClass = Field(
        description="TAN-Medium-Klasse",
    )


class HITAB4(FinTSSegment):
    """TAN-Generator/Liste anzeigen Bestand Rückmeldung, version 4.

    Response with TAN media list.

    Source: FinTS 3.0 Sicherheitsverfahren PIN/TAN
    """

    SEGMENT_TYPE: ClassVar[str] = "HITAB"
    SEGMENT_VERSION: ClassVar[int] = 4

    tan_usage_option: TANUsageOption = Field(
        description="TAN-Einsatzoption",
    )
    tan_media_list: list[TANMedia4] | None = Field(
        default=None,
        max_length=99,
        description="TAN-Medium-Liste",
    )


class HITAB5(FinTSSegment):
    """TAN-Generator/Liste anzeigen Bestand Rückmeldung, version 5.

    Response with TAN media list.

    Source: FinTS 3.0 Sicherheitsverfahren PIN/TAN
    """

    SEGMENT_TYPE: ClassVar[str] = "HITAB"
    SEGMENT_VERSION: ClassVar[int] = 5

    tan_usage_option: TANUsageOption = Field(
        description="TAN-Einsatzoption",
    )
    tan_media_list: list[TANMedia5] | None = Field(
        default=None,
        max_length=99,
        description="TAN-Medium-Liste",
    )


# =============================================================================
# Version Registries
# =============================================================================


HKIDN_VERSIONS: dict[int, type[FinTSSegment]] = {
    2: HKIDN2,
}

HKVVB_VERSIONS: dict[int, type[FinTSSegment]] = {
    3: HKVVB3,
}

HKTAN_VERSIONS: dict[int, type[HKTANBase]] = {
    2: HKTAN2,
    6: HKTAN6,
    7: HKTAN7,
}

HITAN_VERSIONS: dict[int, type[HITANBase]] = {
    6: HITAN6,
    7: HITAN7,
}

HKTAB_VERSIONS: dict[int, type[FinTSSegment]] = {
    4: HKTAB4,
    5: HKTAB5,
}

HITAB_VERSIONS: dict[int, type[FinTSSegment]] = {
    4: HITAB4,
    5: HITAB5,
}


__all__ = [
    # Identification
    "HKIDN2",
    "HKIDN_VERSIONS",
    # Processing
    "HKVVB3",
    "HKVVB_VERSIONS",
    # TAN Request
    "HKTANBase",
    "HKTAN2",
    "HKTAN6",
    "HKTAN7",
    "HKTAN_VERSIONS",
    # TAN Response
    "HITANBase",
    "HITAN6",
    "HITAN7",
    "HITAN_VERSIONS",
    # TAN Media
    "HKTAB4",
    "HKTAB5",
    "HITAB4",
    "HITAB5",
    "HKTAB_VERSIONS",
    "HITAB_VERSIONS",
]

