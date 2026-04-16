"""ApiKeyHash value object."""

from __future__ import annotations

from dataclasses import dataclass

from gateway_admin.domain.errors import DomainError


@dataclass(frozen=True)
class ApiKeyHash:
    """Stored password-grade hash of an API key."""

    value: str

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise DomainError("ApiKeyHash must not be empty")

    def __str__(self) -> str:
        return self.value
