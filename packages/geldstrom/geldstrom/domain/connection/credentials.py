"""Protocol-agnostic credentials for bank connections."""
from __future__ import annotations

from pydantic import BaseModel, SecretStr, computed_field


class BankCredentials(BaseModel, frozen=True):
    """
    Core credentials required to authenticate with a bank.

    This is the protocol-agnostic representation of banking credentials.
    Infrastructure adapters may wrap this with additional protocol-specific
    fields (e.g., FinTS product registration details).
    """

    user_id: str
    secret: SecretStr  # PIN, password, or other authentication secret
    customer_id: str | None = None  # Often same as user_id
    two_factor_method: str | None = None  # Preferred 2FA method identifier
    two_factor_device: str | None = None  # Preferred 2FA device/medium

    @computed_field
    @property
    def effective_customer_id(self) -> str:
        """Return customer_id if set, otherwise user_id."""
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
