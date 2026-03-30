"""Value objects for the consumer access domain."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from gateway.domain import DomainError


class ConsumerStatus(StrEnum):
    """Lifecycle status for an API consumer."""

    ACTIVE = "active"
    DISABLED = "disabled"
    DELETED = "deleted"


@dataclass(frozen=True)
class ApiKeyHash:
    """Stored password-grade hash of an API key."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise DomainError("ApiKeyHash must not be empty")

    def __str__(self) -> str:
        return self.value
