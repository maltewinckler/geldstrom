"""FinTS-specific credentials."""

from __future__ import annotations

from dataclasses import dataclass

from geldstrom.domain import BankCredentials, BankRoute


@dataclass(frozen=True)
class GatewayCredentials:
    """FinTS connection credentials.

    Combines domain-level BankCredentials with FinTS-specific
    connection details (server URL, product registration, etc.).
    """

    route: BankRoute
    server_url: str
    credentials: BankCredentials
    product_id: str
    product_version: str

    @property
    def user_id(self) -> str:
        """Convenience accessor for credentials.user_id."""
        return self.credentials.user_id

    @property
    def pin(self) -> str:
        """Convenience accessor for credentials.secret (unmasked value)."""
        return self.credentials.secret.get_secret_value()

    @property
    def customer_id(self) -> str:
        """Convenience accessor for credentials.effective_customer_id."""
        return self.credentials.effective_customer_id

    @property
    def tan_medium(self) -> str | None:
        """Convenience accessor for credentials.two_factor_device."""
        return self.credentials.two_factor_device

    @property
    def tan_method(self) -> str | None:
        """Convenience accessor for credentials.two_factor_method."""
        return self.credentials.two_factor_method

    def masked(self) -> dict[str, str]:
        """Return credentials with sensitive values masked."""
        return {
            "route": str(self.route),
            "server_url": self.server_url,
            "product_id": self.product_id,
            "product_version": self.product_version,
            **{k: str(v) for k, v in self.credentials.masked().items()},
        }


__all__ = ["GatewayCredentials"]
