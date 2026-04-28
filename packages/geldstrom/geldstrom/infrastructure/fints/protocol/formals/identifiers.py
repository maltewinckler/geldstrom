"""FinTS Identifier DEGs - Bank and Account Identifiers."""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, Field, field_validator

from ..base import FinTSDataElementGroup
from ..types import FinTSAlphanumeric, FinTSBool, FinTSCountry, FinTSID


class SEPAAccount(BaseModel, frozen=True):
    """SEPA account representation for internal data transfer."""

    iban: str
    bic: str | None = None
    accountnumber: str
    subaccount: str = ""
    blz: str | None = None

    @field_validator("subaccount", mode="before")
    @classmethod
    def _coerce_subaccount(cls, v: str | None) -> str:
        return v or ""


# Country code mappings (ISO 3166-1 alpha-2 <-> ISO 3166-1 numeric)
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

    bank_code is optional - some banks (e.g., DKB) send incomplete data with only the country code.
    """

    country_identifier: FinTSCountry = Field(
        description="Länderkennzeichen (ISO 3166-1 numeric)",
    )
    bank_code: FinTSAlphanumeric | None = Field(
        default=None,
        max_length=30,
        description="Kreditinstitutscode (BLZ in Germany)",
    )

    # Class-level country code mappings
    COUNTRY_ALPHA_TO_NUMERIC: ClassVar[dict[str, str]] = COUNTRY_ALPHA_TO_NUMERIC
    COUNTRY_NUMERIC_TO_ALPHA: ClassVar[dict[str, str]] = COUNTRY_NUMERIC_TO_ALPHA

    @property
    def country_alpha(self) -> str | None:
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
    """Kontoverbindung (Account Identifier) - Version 3."""

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
    def from_sepa_account(cls, account) -> AccountIdentifier:
        return cls(
            account_number=account.accountnumber,
            subaccount_number=account.subaccount or "",
            bank_identifier=BankIdentifier(
                country_identifier=COUNTRY_ALPHA_TO_NUMERIC.get(account.bic[4:6], "280")
                if account.bic
                else "280",
                bank_code=account.blz,
            ),
        )


class AccountInternational(FinTSDataElementGroup):
    """Kontoverbindung international (KTI1)."""

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
    def from_sepa_account(cls, account) -> AccountInternational:
        return cls(
            iban=account.iban,
            bic=account.bic,
        )


class AccountInternationalSEPA(FinTSDataElementGroup):
    """Kontoverbindung ZV international (KTZ1)."""

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

    def as_sepa_account(self) -> SEPAAccount | None:
        """Convert to SEPAAccount model."""
        if not self.is_sepa:
            return None
        blz = None
        if self.bank_identifier and self.bank_identifier.bank_code:
            blz = self.bank_identifier.bank_code
        return SEPAAccount(
            iban=self.iban,
            bic=self.bic,
            accountnumber=self.account_number,
            subaccount=self.subaccount_number or "",
            blz=blz,
        )

    @classmethod
    def from_sepa_account(cls, account) -> AccountInternationalSEPA:
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
    "SEPAAccount",
]
