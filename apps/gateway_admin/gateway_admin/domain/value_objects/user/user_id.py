"""UserId value object."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class UserId:
    """Strongly typed entity identifier for users."""

    value: UUID

    @classmethod
    def from_string(cls, raw: str) -> UserId:
        return cls(UUID(raw))

    def __str__(self) -> str:
        return str(self.value)
