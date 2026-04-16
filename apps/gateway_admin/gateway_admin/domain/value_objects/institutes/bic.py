"""Bic value object."""

from __future__ import annotations

import re
from dataclasses import dataclass

from gateway_admin.domain.errors import DomainError

_BIC_PATTERN = re.compile(r"^[A-Z0-9]{8}([A-Z0-9]{3})?$")


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
