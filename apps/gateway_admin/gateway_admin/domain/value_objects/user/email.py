"""Email value object."""

from __future__ import annotations

import re
from dataclasses import dataclass

from gateway_admin.domain.errors import DomainError

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class Email:
    """Normalized, validated email address."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().casefold()
        if not _EMAIL_PATTERN.match(normalized):
            raise DomainError("Email must contain a valid email address")
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value
