"""Transient value objects for bank-facing gateway operations."""

from __future__ import annotations

import re

from pydantic import BaseModel, RootModel, SecretStr, field_validator

from gateway.domain import DomainError

_IBAN_PATTERN = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{11,30}$")
_BLZ_PATTERN = re.compile(r"^\d{8}$")


def _iban_checksum_is_valid(iban: str) -> bool:
    rearranged = iban[4:] + iban[:4]
    numeric = "".join(str(int(character, 36)) for character in rearranged)
    return int(numeric) % 97 == 1


class BankLeitzahl(RootModel[str], frozen=True):
    """German bank routing number."""

    @field_validator("root")
    @classmethod
    def _validate_blz(cls, v: str) -> str:
        if not _BLZ_PATTERN.match(v):
            raise DomainError("BankLeitzahl must be an 8-digit string")
        return v

    @property
    def value(self) -> str:
        return self.root

    def __str__(self) -> str:
        return self.root


class RequestedIban(RootModel[str], frozen=True):
    """Normalized IBAN selected for transaction retrieval."""

    @field_validator("root", mode="before")
    @classmethod
    def _normalize_and_validate_iban(cls, v: object) -> str:
        normalized = "".join(str(v).split()).upper()
        if not _IBAN_PATTERN.match(normalized):
            raise DomainError("RequestedIban must be a valid IBAN")
        if not _iban_checksum_is_valid(normalized):
            raise DomainError("RequestedIban must satisfy the IBAN checksum")
        return normalized

    @property
    def value(self) -> str:
        return self.root

    def __str__(self) -> str:
        return self.root


class PresentedBankCredentials(BaseModel):
    """Opaque credential pair passed to the banking connector."""

    model_config = {"frozen": True}

    user_id: SecretStr
    password: SecretStr
    tan_method: str | None = None
    tan_medium: str | None = None

    @field_validator("user_id", "password", mode="before")
    @classmethod
    def _must_not_be_blank(cls, value: object) -> object:
        raw = value.get_secret_value() if isinstance(value, SecretStr) else value
        if isinstance(raw, str) and not raw.strip():
            raise ValueError("must not be blank")
        return value
