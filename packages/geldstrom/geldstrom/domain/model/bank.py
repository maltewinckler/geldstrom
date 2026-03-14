"""Domain objects describing banks and their capabilities."""
from __future__ import annotations

from typing import FrozenSet, Mapping

from pydantic import BaseModel, field_validator


class BankRoute(BaseModel, frozen=True):
    """Light-weight identifier describing how to reach a bank backend."""

    country_code: str
    bank_code: str

    @field_validator("country_code", mode="before")
    @classmethod
    def normalize_country_code(cls, v: str) -> str:
        return v.upper()

    def as_tuple(self) -> tuple[str, str]:
        return self.country_code, self.bank_code

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.country_code}-{self.bank_code}"


class BankCapabilities(BaseModel, frozen=True):
    """Describes which FinTS operations the bank exposes to this user."""

    supported_operations: FrozenSet[str] = frozenset()
    supported_formats: Mapping[str, tuple[str, ...]] = {}

    def supports(self, operation: str) -> bool:
        return operation in self.supported_operations
