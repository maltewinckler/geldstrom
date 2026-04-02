"""Transient value objects for bank-facing gateway operations."""

from __future__ import annotations

import re
from dataclasses import dataclass

from pydantic import BaseModel, SecretStr, field_validator

from gateway.domain import DomainError

_IBAN_PATTERN = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{11,30}$")
_BLZ_PATTERN = re.compile(r"^\d{8}$")


def _iban_checksum_is_valid(iban: str) -> bool:
    rearranged = iban[4:] + iban[:4]
    numeric = "".join(str(int(character, 36)) for character in rearranged)
    return int(numeric) % 97 == 1


@dataclass(frozen=True)
class BankLeitzahl:
    """German bank routing number."""

    value: str

    def __post_init__(self) -> None:
        if not _BLZ_PATTERN.match(self.value):
            raise DomainError("BankLeitzahl must be an 8-digit string")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class RequestedIban:
    """Normalized IBAN selected for transaction retrieval."""

    value: str

    def __post_init__(self) -> None:
        normalized = "".join(self.value.split()).upper()
        if not _IBAN_PATTERN.match(normalized):
            raise DomainError("RequestedIban must be a valid IBAN")
        if not _iban_checksum_is_valid(normalized):
            raise DomainError("RequestedIban must satisfy the IBAN checksum")
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value


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
