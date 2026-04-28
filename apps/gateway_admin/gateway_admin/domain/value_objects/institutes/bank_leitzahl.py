"""BankLeitzahl value object."""

from __future__ import annotations

import re
from dataclasses import dataclass

from gateway_admin.domain.errors import DomainError

_BLZ_PATTERN = re.compile(r"^\d{8}$")


@dataclass(frozen=True)
class BankLeitzahl:
    """German bank routing number."""

    value: str

    def __post_init__(self) -> None:
        if not _BLZ_PATTERN.match(self.value):
            raise DomainError("BankLeitzahl must be an 8-digit string")

    def __str__(self) -> str:
        return self.value
