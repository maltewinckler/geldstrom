"""Value objects for the institution catalog domain."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from gateway.domain.shared import DomainError

_BLZ_PATTERN = re.compile(r"^\d{8}$")
_BIC_PATTERN = re.compile(r"^[A-Z0-9]{8}([A-Z0-9]{3})?$")


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
class Bic:
    """Bank identifier code."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().upper()
        if not _BIC_PATTERN.match(normalized):
            raise DomainError("Bic must be 8 or 11 alphanumeric characters")
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class InstituteEndpoint:
    """PIN/TAN endpoint URL used by the banking connector."""

    value: str

    def __post_init__(self) -> None:
        parsed = urlparse(self.value)
        if parsed.scheme != "https" or not parsed.netloc:
            raise DomainError("InstituteEndpoint must be an https URL")

    def __str__(self) -> str:
        return self.value
