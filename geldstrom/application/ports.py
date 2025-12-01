"""Application layer ports and credential objects."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol, Sequence

from geldstrom.domain import (
    Account,
    BalanceSnapshot,
    BankCapabilities,
    BankCredentials,
    BankRoute,
    SessionToken,
    TransactionFeed,
)


@dataclass(frozen=True)
class GatewayCredentials:
    """Input data required to talk to a bank backend.

    Combines domain-level BankCredentials with infrastructure-specific
    connection details (server URL, FinTS product registration, etc.).
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
        return {
            "route": str(self.route),
            "server_url": self.server_url,
            "product_id": self.product_id,
            "product_version": self.product_version,
            **{k: str(v) for k, v in self.credentials.masked().items()},
        }


class BankGateway(Protocol):
    """Boundary for infrastructure adapters.

    Uses SessionToken protocol for session management, allowing different
    infrastructure implementations (FinTS 3.0, PSD2, etc.) to provide their
    own session state types.
    """

    def open_session(
        self,
        credentials: GatewayCredentials,
        existing_state: SessionToken | None = None,
    ) -> SessionToken:
        ...

    def fetch_bank_capabilities(
        self,
        credentials: GatewayCredentials,
        session: SessionToken,
    ) -> BankCapabilities:
        ...

    def fetch_accounts(
        self,
        credentials: GatewayCredentials,
        session: SessionToken,
    ) -> Sequence[Account]:
        ...

    def fetch_balance(
        self,
        credentials: GatewayCredentials,
        session: SessionToken,
        account: Account,
    ) -> BalanceSnapshot:
        ...

    def fetch_transactions(
        self,
        credentials: GatewayCredentials,
        session: SessionToken,
        account: Account,
        start_date: date | None,
        end_date: date | None,
    ) -> TransactionFeed:
        ...
