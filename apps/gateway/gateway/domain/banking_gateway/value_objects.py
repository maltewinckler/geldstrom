"""Transient value objects for bank-facing gateway operations."""

from __future__ import annotations

import re
from dataclasses import dataclass

from pydantic import SecretStr

from gateway.domain.consumer_access import ConsumerId
from gateway.domain.shared import DomainError

_IBAN_PATTERN = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{11,30}$")


def _iban_checksum_is_valid(iban: str) -> bool:
    rearranged = iban[4:] + iban[:4]
    numeric = "".join(str(int(character, 36)) for character in rearranged)
    return int(numeric) % 97 == 1


@dataclass(frozen=True)
class PresentedBankUserId:
    """Opaque user identifier that must not be logged in plaintext."""

    value: SecretStr


@dataclass(frozen=True)
class PresentedBankPassword:
    """Opaque bank password or PIN that must not be logged in plaintext."""

    value: SecretStr


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


@dataclass(frozen=True)
class AuthenticatedConsumer:
    """Authenticated API consumer identity carried through bank-facing use cases."""

    consumer_id: ConsumerId


@dataclass(frozen=True)
class PresentedBankCredentials:
    """Opaque credential pair passed to the banking connector."""

    user_id: PresentedBankUserId
    password: PresentedBankPassword
