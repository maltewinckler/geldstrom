"""FinTS Bank Parameter Segments.

These segments handle bank and user parameter data:
- Bank Parameter Data (BPD): HIBPA
- User Parameter Data (UPD): HIUPA, HIUPD
- Communication Access: HKKOM, HIKOM
"""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from ..base import FinTSDataElementGroup, FinTSSegment
from ..formals import (
    AccountLimit,
    AllowedTransaction,
    BankIdentifier,
    CommunicationParameter,
    Language,
    UPDUsage,
)
from ..types import (
    FinTSAlphanumeric,
    FinTSCode,
    FinTSCurrency,
    FinTSID,
    FinTSNumeric,
)

# =============================================================================
# Supporting DEGs for Bank Segments
# =============================================================================


class SupportedLanguages(FinTSDataElementGroup):
    """Unterstützte Sprachen DEG for inline embedding."""

    languages: list[Language] = Field(
        min_length=1,
        max_length=9,
        description="Unterstützte Dialogsprachen",
    )


class SupportedHBCIVersions(FinTSDataElementGroup):
    """Unterstützte HBCI-Versionen DEG for inline embedding."""

    versions: list[FinTSCode] = Field(
        min_length=1,
        max_length=9,
        description="Unterstützte HBCI-Versionen",
    )


class AccountInformationDEG(FinTSDataElementGroup):
    """Kontoinformation DEG (for HIUPD6 reference)."""

    account_number: FinTSID = Field(
        description="Konto-/Depotnummer",
    )
    subaccount_number: FinTSID | None = Field(
        default=None,
        description="Unterkontomerkmal",
    )
    bank_identifier: BankIdentifier = Field(
        description="Kreditinstitutskennung",
    )


# =============================================================================
# Bank Parameter Data (BPD)
# =============================================================================


class HIBPA3(FinTSSegment):
    """Bankparameter allgemein (Bank Parameters), version 3.

    Contains general bank parameters including supported languages,
    versions, and limits.

    Source: FinTS 3.0 Formals
    """

    SEGMENT_TYPE: ClassVar[str] = "HIBPA"
    SEGMENT_VERSION: ClassVar[int] = 3

    bpd_version: FinTSNumeric = Field(
        ge=0,
        lt=1000,
        description="BPD-Version",
    )
    bank_identifier: BankIdentifier = Field(
        description="Kreditinstitutskennung",
    )
    bank_name: FinTSAlphanumeric = Field(
        max_length=60,
        description="Kreditinstitutsbezeichnung",
    )
    number_tasks: FinTSNumeric = Field(
        ge=0,
        lt=1000,
        description="Anzahl Geschäftsvorfallarten pro Nachricht",
    )
    supported_languages: list[Language] = Field(
        min_length=1,
        max_length=9,
        description="Unterstützte Sprachen",
    )
    supported_hbci_versions: list[FinTSCode] = Field(
        min_length=1,
        max_length=9,
        description="Unterstützte HBCI-Versionen",
    )
    max_message_length: FinTSNumeric | None = Field(
        default=None,
        ge=0,
        lt=10000,
        description="Maximale Nachrichtengröße",
    )
    min_timeout: FinTSNumeric | None = Field(
        default=None,
        ge=0,
        lt=10000,
        description="Minimaler Timeout-Wert (Sekunden)",
    )
    max_timeout: FinTSNumeric | None = Field(
        default=None,
        ge=0,
        lt=10000,
        description="Maximaler Timeout-Wert (Sekunden)",
    )


# =============================================================================
# User Parameter Data (UPD)
# =============================================================================


class HIUPA4(FinTSSegment):
    """Userparameter allgemein (User Parameters), version 4.

    Contains general user parameters.

    Source: FinTS 3.0 Formals
    """

    SEGMENT_TYPE: ClassVar[str] = "HIUPA"
    SEGMENT_VERSION: ClassVar[int] = 4

    user_identifier: FinTSID = Field(
        description="Benutzerkennung",
    )
    upd_version: FinTSNumeric = Field(
        ge=0,
        lt=1000,
        description="UPD-Version",
    )
    upd_usage: UPDUsage = Field(
        description="UPD-Verwendung",
    )
    username: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=35,
        description="Benutzername",
    )
    extension: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=2048,
        description="Erweiterung, allgemein",
    )


class HIUPD6(FinTSSegment):
    """Kontoinformationen (Account Information), version 6.

    Contains detailed information about a user's account.

    Source: FinTS 3.0 Formals
    """

    SEGMENT_TYPE: ClassVar[str] = "HIUPD"
    SEGMENT_VERSION: ClassVar[int] = 6

    account_information: AccountInformationDEG | None = Field(
        default=None,
        description="Kontoverbindung",
    )
    iban: FinTSAlphanumeric = Field(
        max_length=34,
        description="IBAN",
    )
    customer_id: FinTSID = Field(
        description="Kunden-ID",
    )
    account_type: FinTSNumeric = Field(
        ge=0,
        lt=100,
        description="Kontoart",
    )
    account_currency: FinTSCurrency = Field(
        description="Kontowährung",
    )
    name_account_owner_1: FinTSAlphanumeric = Field(
        max_length=27,
        description="Name des Kontoinhabers 1",
    )
    name_account_owner_2: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=27,
        description="Name des Kontoinhabers 2",
    )
    account_product_name: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=30,
        description="Kontoproduktbezeichnung",
    )
    account_limit: AccountLimit | None = Field(
        default=None,
        description="Kontolimit",
    )
    allowed_transactions: list[AllowedTransaction] | None = Field(
        default=None,
        max_length=999,
        description="Erlaubte Geschäftsvorfälle",
    )
    extension: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=2048,
        description="Erweiterung, kontobezogen",
    )


# =============================================================================
# Communication Access
# =============================================================================


class HKKOM4(FinTSSegment):
    """Kommunikationszugang anfordern (Request Communication Access), version 4.

    Request to get communication parameters for banks.

    Source: FinTS 3.0 Formals
    """

    SEGMENT_TYPE: ClassVar[str] = "HKKOM"
    SEGMENT_VERSION: ClassVar[int] = 4

    start_bank_identifier: BankIdentifier | None = Field(
        default=None,
        description="Von Kreditinstitutskennung",
    )
    end_bank_identifier: BankIdentifier | None = Field(
        default=None,
        description="Bis Kreditinstitutskennung",
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


class HIKOM4(FinTSSegment):
    """Kommunikationszugang rückmelden (Communication Access Response), version 4.

    Response with communication parameters for a bank.

    Source: FinTS 3.0 Formals
    """

    SEGMENT_TYPE: ClassVar[str] = "HIKOM"
    SEGMENT_VERSION: ClassVar[int] = 4

    bank_identifier: BankIdentifier = Field(
        description="Kreditinstitutskennung",
    )
    default_language: Language = Field(
        description="Standardsprache",
    )
    communication_parameters: list[CommunicationParameter] = Field(
        min_length=1,
        max_length=9,
        description="Kommunikationsparameter",
    )


# =============================================================================
# Version Registries
# =============================================================================
HIBPA_VERSIONS: dict[int, type[FinTSSegment]] = {3: HIBPA3}
HIUPA_VERSIONS: dict[int, type[FinTSSegment]] = {4: HIUPA4}
HIUPD_VERSIONS: dict[int, type[FinTSSegment]] = {6: HIUPD6}
HKKOM_VERSIONS: dict[int, type[FinTSSegment]] = {4: HKKOM4}
HIKOM_VERSIONS: dict[int, type[FinTSSegment]] = {4: HIKOM4}


__all__ = [
    # Supporting DEGs
    "SupportedLanguages",
    "SupportedHBCIVersions",
    "AccountInformationDEG",
    # BPD
    "HIBPA3",
    "HIBPA_VERSIONS",
    # UPD
    "HIUPA4",
    "HIUPD6",
    "HIUPA_VERSIONS",
    "HIUPD_VERSIONS",
    # Communication
    "HKKOM4",
    "HIKOM4",
    "HKKOM_VERSIONS",
    "HIKOM_VERSIONS",
]
