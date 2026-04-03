"""FinTS-specific credentials."""

from __future__ import annotations

from dataclasses import dataclass

from geldstrom.domain import BankCredentials, BankRoute


@dataclass(frozen=True)
class GatewayCredentials:
    """FinTS connection credentials including server URL and product registration."""

    route: BankRoute
    server_url: str
    credentials: BankCredentials
    product_id: str
    product_version: str

    @property
    def user_id(self) -> str:
        return self.credentials.user_id

    @property
    def pin(self) -> str:
        return self.credentials.secret.get_secret_value()

    @property
    def customer_id(self) -> str:
        return self.credentials.effective_customer_id

    @property
    def tan_medium(self) -> str | None:
        return self.credentials.two_factor_device

    @property
    def tan_method(self) -> str | None:
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
