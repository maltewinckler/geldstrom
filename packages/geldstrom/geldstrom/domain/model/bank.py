"""Domain objects describing banks and their capabilities."""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, SecretStr, computed_field, field_validator


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

    supported_operations: frozenset[str] = frozenset()
    supported_formats: Mapping[str, tuple[str, ...]] = {}

    def supports(self, operation: str) -> bool:
        return operation in self.supported_operations


class BankCredentials(BaseModel, frozen=True):
    """Protocol-agnostic credentials for authenticating with a bank."""

    user_id: str
    secret: SecretStr
    customer_id: str | None = None
    two_factor_method: str | None = None
    two_factor_device: str | None = None

    @computed_field
    @property
    def effective_customer_id(self) -> str:
        return self.customer_id or self.user_id

    def masked(self) -> dict[str, str | None]:
        """Return a representation safe for logging."""
        return {
            "user_id": self.user_id,
            "customer_id": self.effective_customer_id,
            "two_factor_method": self.two_factor_method or "<auto>",
            "two_factor_device": self.two_factor_device or "<default>",
            "secret": "***",
        }
