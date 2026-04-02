"""Protocol-agnostic credentials for bank connections."""

from __future__ import annotations

from pydantic import BaseModel, SecretStr, computed_field


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


__all__ = ["BankCredentials"]
