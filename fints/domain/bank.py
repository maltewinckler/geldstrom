"""Domain objects describing banks and their advertised capabilities."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet, Mapping


@dataclass(frozen=True)
class BankRoute:
    """Light-weight identifier describing how to reach a bank backend."""

    country_code: str
    bank_code: str

    def __post_init__(self):
        object.__setattr__(self, "country_code", self.country_code.upper())
        object.__setattr__(self, "bank_code", self.bank_code)

    def as_tuple(self) -> tuple[str, str]:
        return self.country_code, self.bank_code

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.country_code}-{self.bank_code}"


@dataclass(frozen=True)
class BankCapabilities:
    """Describes which FinTS operations the bank exposes to this user."""

    supported_operations: FrozenSet[str] = field(default_factory=frozenset)
    supported_formats: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    def supports(self, operation: str) -> bool:
        return operation in self.supported_operations
