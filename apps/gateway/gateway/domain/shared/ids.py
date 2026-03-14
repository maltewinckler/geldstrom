"""Shared identifier value objects."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class EntityId:
    """Base value object for entity identifiers backed by UUIDs."""

    value: UUID

    @classmethod
    def from_string(cls, raw_value: str) -> EntityId:
        return cls(UUID(raw_value))

    def __str__(self) -> str:
        return str(self.value)
