"""FinTS Identifier DEGs - Bank and Account Identifiers.

These DEGs identify banks and accounts in FinTS messages.
"""
from __future__ import annotations

from typing import ClassVar

from pydantic import Field, model_validator

from ..base import FinTSDataElementGroup
from ..types import FinTSAlphanumeric, FinTSCountry, FinTSID, FinTSBool

# Country code mappings (ISO 3166-1 alpha-2 <-> ISO 3166-1 numeric)
# Source: FinTS 3.0 Kapitel E.4 der SEPA-Geschäftsvorfälle
COUNTRY_ALPHA_TO_NUMERIC: dict[str, str] = {
    "BE": "056",
    "BG": "100",
    "DK": "208",
    "DE": "280",
    "FI": "246",
    "FR": "250",
    "GR": "300",
    "GB": "826",
    "IE": "372",
    "IS": "352",
    "IT": "380",
    "JP": "392",
    "CA": "124",
    "HR": "191",
    "LI": "438",
    "LU": "442",
    "NL": "528",
    "AT": "040",
    "PL": "616",
    "PT": "620",
    "RO": "642",
    "RU": "643",
    "SE": "752",
    "CH": "756",
    "SK": "703",
    "SI": "705",
    "ES": "724",
    "CZ": "203",
    "TR": "792",
    "HU": "348",
    "US": "840",
    "EU": "978",
}

COUNTRY_NUMERIC_TO_ALPHA: dict[str, str] = {
    v: k for k, v in COUNTRY_ALPHA_TO_NUMERIC.items()
}
# Add alternative German code
COUNTRY_NUMERIC_TO_ALPHA["276"] = "DE"


class BankIdentifier(FinTSDataElementGroup):
    """Kreditinstitutskennung (Bank Identifier).

    Identifies a bank using country code and bank code (BLZ in Germany).

    Source: FinTS 3.0 Formals

    Example:
        bank = BankIdentifier(country_identifier="280", bank_code="12345678")
        bank = BankIdentifier.from_wire_list(["280", "12345678"])
    """

    country_identifier: FinTSCountry = Field(
        description="Länderkennzeichen (ISO 3166-1 numeric)",
    )
    bank_code: FinTSAlphanumeric = Field(
        max_length=30,
        description="Kreditinstitutscode (BLZ in Germany)",
    )

    # Class-level country code mappings
    COUNTRY_ALPHA_TO_NUMERIC: ClassVar[dict[str, str]] = COUNTRY_ALPHA_TO_NUMERIC
    COUNTRY_NUMERIC_TO_ALPHA: ClassVar[dict[str, str]] = COUNTRY_NUMERIC_TO_ALPHA

    @property
    def country_alpha(self) -> str | None:
        """Get ISO 3166-1 alpha-2 country code."""
        return COUNTRY_NUMERIC_TO_ALPHA.get(self.country_identifier)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BankIdentifier):
            return NotImplemented
        return (
            self.country_identifier == other.country_identifier
            and self.bank_code == other.bank_code
        )

    def __hash__(self) -> int:
        return hash((self.country_identifier, self.bank_code))


class AccountIdentifier(FinTSDataElementGroup):
    """Kontoverbindung (Account Identifier) - Version 3.

    Identifies an account using account number, subaccount, and bank.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle

    Example:
        account = AccountIdentifier(
            account_number="1234567890",
            subaccount_number="00",
            bank_identifier=BankIdentifier(country_identifier="280", bank_code="12345678"),
        )
    """

    account_number: FinTSID = Field(
        description="Konto-/Depotnummer",
    )
    subaccount_number: FinTSID = Field(
        description="Unterkontomerkmal",
    )
    bank_identifier: BankIdentifier = Field(
        description="Kreditinstitutskennung",
    )

    @classmethod
    def from_sepa_account(cls, account) -> "AccountIdentifier":
        """Create from SEPAAccount model."""
        return cls(
            account_number=account.accountnumber,
            subaccount_number=account.subaccount or "",
            bank_identifier=BankIdentifier(
                country_identifier=COUNTRY_ALPHA_TO_NUMERIC.get(
                    account.bic[4:6], "280"
                ) if account.bic else "280",
                bank_code=account.blz,
            ),
        )


class AccountInternational(FinTSDataElementGroup):
    """Kontoverbindung international (KTI1).

    International account identifier with optional IBAN/BIC.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    iban: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=34,
        description="IBAN",
    )
    bic: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=11,
        description="BIC",
    )
    account_number: FinTSID | None = Field(
        default=None,
        description="Konto-/Depotnummer",
    )
    subaccount_number: FinTSID | None = Field(
        default=None,
        description="Unterkontomerkmal",
    )
    bank_identifier: BankIdentifier | None = Field(
        default=None,
        description="Kreditinstitutskennung",
    )

    @classmethod
    def from_sepa_account(cls, account) -> "AccountInternational":
        """Create from SEPAAccount model."""
        return cls(
            iban=account.iban,
            bic=account.bic,
        )


class AccountInternationalSEPA(FinTSDataElementGroup):
    """Kontoverbindung ZV international (KTZ1).

    SEPA account identifier with is_sepa flag.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    is_sepa: FinTSBool = Field(
        description="Kontoverwendung SEPA",
    )
    iban: FinTSAlphanumeric = Field(
        max_length=34,
        description="IBAN",
    )
    bic: FinTSAlphanumeric = Field(
        max_length=11,
        description="BIC",
    )
    account_number: FinTSID = Field(
        description="Konto-/Depotnummer",
    )
    subaccount_number: FinTSID = Field(
        description="Unterkontomerkmal",
    )
    bank_identifier: BankIdentifier = Field(
        description="Kreditinstitutskennung",
    )

    def as_sepa_account(self):
        """Convert to SEPAAccount model."""
        from geldstrom.models import SEPAAccount
        if not self.is_sepa:
            return None
        return SEPAAccount(
            self.iban,
            self.bic,
            self.account_number,
            self.subaccount_number,
            self.bank_identifier.bank_code,
        )

    @classmethod
    def from_sepa_account(cls, account) -> "AccountInternationalSEPA":
        """Create from SEPAAccount model."""
        return cls(
            is_sepa=True,
            iban=account.iban,
            bic=account.bic,
            account_number=account.accountnumber,
            subaccount_number=account.subaccount or "",
            bank_identifier=BankIdentifier(
                country_identifier=COUNTRY_ALPHA_TO_NUMERIC.get(
                    account.bic[4:6], "280"
                ),
                bank_code=account.blz,
            ),
        )


__all__ = [
    "COUNTRY_ALPHA_TO_NUMERIC",
    "COUNTRY_NUMERIC_TO_ALPHA",
    "BankIdentifier",
    "AccountIdentifier",
    "AccountInternational",
    "AccountInternationalSEPA",
]

