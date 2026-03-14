"""FinTS Parameter Data Element Groups (DEGs).

This module contains Pydantic models for BPD (Bank Parameter Data)
and UPD (User Parameter Data) related structures.
"""
from __future__ import annotations

from pydantic import Field

from ..base import FinTSDataElementGroup
from ..types import (
    FinTSAlphanumeric,
    FinTSCode,
    FinTSNumeric,
)
from .enums import Language, ServiceType
from .identifiers import BankIdentifier

# =============================================================================
# Language and Version DEGs
# =============================================================================


class SupportedLanguages(FinTSDataElementGroup):
    """Unterstützte Sprachen.

    Lists languages supported by the bank for dialog communication.

    Source: FinTS 3.0 Formals
    """

    languages: list[Language] = Field(
        min_length=1,
        max_length=9,
        description="Unterstützte Dialogsprachen",
    )


class SupportedHBCIVersions(FinTSDataElementGroup):
    """Unterstützte HBCI-Versionen.

    Lists FinTS/HBCI protocol versions supported by the bank.

    Source: FinTS 3.0 Formals
    """

    versions: list[FinTSCode] = Field(
        min_length=1,
        max_length=9,
        description="Unterstützte HBCI-Versionen",
    )


# =============================================================================
# Communication DEGs
# =============================================================================


class CommunicationParameter(FinTSDataElementGroup):
    """Kommunikationsparameter.

    Defines connection parameters for a specific service type.

    Source: FinTS 3.0 Formals
    """

    service_type: ServiceType = Field(
        description="Kommunikationsdienst",
    )
    address: FinTSAlphanumeric = Field(
        max_length=512,
        description="Kommunikationsadresse (URL)",
    )
    address_adjunct: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=512,
        description="Kommunikationsadresszusatz",
    )
    filter_function: FinTSAlphanumeric | None = Field(
        default=None,
        min_length=3,
        max_length=3,
        description="Filterfunktion",
    )
    filter_function_version: FinTSNumeric | None = Field(
        default=None,
        ge=0,
        lt=1000,
        description="Version der Filterfunktion",
    )


class CommunicationAccess(FinTSDataElementGroup):
    """Kommunikationszugang.

    Groups communication parameters for multiple access methods.

    Source: FinTS 3.0 Formals
    """

    parameters: list[CommunicationParameter] = Field(
        min_length=1,
        max_length=9,
        description="Kommunikationsparameter",
    )


# =============================================================================
# Account Information DEGs
# =============================================================================


class AccountLimit(FinTSDataElementGroup):
    """Kontolimit.

    Defines transaction limits for an account.

    Source: FinTS 3.0 Formals
    """

    limit_type: FinTSCode | None = Field(
        default=None,
        description="Limitart",
    )
    limit_amount: FinTSNumeric | None = Field(
        default=None,
        description="Limitbetrag",
    )
    limit_currency: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=3,
        description="Limitwährung",
    )
    limit_days: FinTSNumeric | None = Field(
        default=None,
        description="Limittage",
    )


class AllowedTransaction(FinTSDataElementGroup):
    """Erlaubter Geschäftsvorfall.

    Defines a transaction type allowed for an account.

    Source: FinTS 3.0 Formals
    """

    transaction_code: FinTSAlphanumeric = Field(
        max_length=6,
        description="Geschäftsvorfallcode",
    )
    required_signatures: FinTSNumeric = Field(
        ge=0,
        lt=10,
        description="Anzahl benötigter Signaturen",
    )
    limit: AccountLimit | None = Field(
        default=None,
        description="Limit für Geschäftsvorfall",
    )


class AccountInformation(FinTSDataElementGroup):
    """Kontoinformation (UPD-Eintrag).

    Detailed information about a user's account from UPD.

    Source: FinTS 3.0 Formals
    """

    account_number: FinTSAlphanumeric = Field(
        max_length=30,
        description="Kontonummer",
    )
    subaccount_number: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=30,
        description="Unterkontomerkmal",
    )
    bank_identifier: BankIdentifier = Field(
        description="Kreditinstitutskennung",
    )
    customer_id: FinTSAlphanumeric = Field(
        max_length=30,
        description="Kunden-ID",
    )
    account_type: FinTSNumeric | None = Field(
        default=None,
        description="Kontoart",
    )
    account_currency: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=3,
        description="Kontowährung",
    )
    account_holder_name_1: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=35,
        description="Name des Kontoinhabers 1",
    )
    account_holder_name_2: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=35,
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
        description="Erlaubte Geschäftsvorfälle",
    )


# =============================================================================
# SEPA Account Parameter DEGs
# =============================================================================


class GetSEPAAccountParameter(FinTSDataElementGroup):
    """Parameter SEPA-Kontoverbindung anfordern.

    Defines parameters for SEPA account information requests.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    single_account_query_allowed: bool = Field(
        description="Einzelkontenabruf erlaubt",
    )
    national_account_allowed: bool = Field(
        description="Nationale Kontoverbindung erlaubt",
    )
    structured_usage_allowed: bool | None = Field(
        default=None,
        description="Strukturierter Verwendungszweck erlaubt",
    )
    supported_sepa_formats: list[FinTSAlphanumeric] | None = Field(
        default=None,
        max_length=9,
        description="Unterstützte SEPA-Datenformate",
    )


__all__ = [
    # Language/Version
    "SupportedLanguages",
    "SupportedHBCIVersions",
    # Communication
    "CommunicationParameter",
    "CommunicationAccess",
    # Account
    "AccountLimit",
    "AllowedTransaction",
    "AccountInformation",
    # SEPA
    "GetSEPAAccountParameter",
]

