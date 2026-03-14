"""Value objects for the consumer access domain."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from gateway.domain.shared import DomainError, EntityId

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ConsumerStatus(StrEnum):
    """Lifecycle status for an API consumer."""

    ACTIVE = "active"
    DISABLED = "disabled"
    DELETED = "deleted"


@dataclass(frozen=True)
class ConsumerId(EntityId):
    """Strongly typed entity identifier for API consumers."""


@dataclass(frozen=True)
class EmailAddress:
    """Normalized email address used as an operator-facing identifier."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().casefold()
        if not _EMAIL_PATTERN.match(normalized):
            raise DomainError("EmailAddress must contain a valid email address")
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class ApiKeyHash:
    """Stored password-grade hash of an API key."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise DomainError("ApiKeyHash must not be empty")

    def __str__(self) -> str:
        return self.value
