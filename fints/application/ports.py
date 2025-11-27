"""Application layer ports and credential objects."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol, Sequence

from fints.domain import (
    Account,
    BalanceSnapshot,
    BankCapabilities,
    BankRoute,
    SessionState,
    TransactionFeed,
)


@dataclass(frozen=True)
class GatewayCredentials:
    """Input data required to talk to a bank backend."""

    route: BankRoute
    server_url: str
    user_id: str
    pin: str
    product_id: str
    product_version: str
    customer_id: str | None = None
    tan_medium: str | None = None
    tan_method: str | None = None

    def masked(self) -> dict[str, str]:
        return {
            "route": str(self.route),
            "server_url": self.server_url,
            "user_id": self.user_id,
            "product_id": self.product_id,
            "product_version": self.product_version,
            "customer_id": self.customer_id or self.user_id,
            "tan_medium": self.tan_medium or "<default>",
            "tan_method": self.tan_method or "<auto>",
        }


class BankGateway(Protocol):
    """Boundary for infrastructure adapters."""

    def open_session(
        self,
        credentials: GatewayCredentials,
        existing_state: SessionState | None = None,
    ) -> SessionState:
        ...

    def fetch_bank_capabilities(
        self,
        credentials: GatewayCredentials,
        session: SessionState,
    ) -> BankCapabilities:
        ...

    def fetch_accounts(
        self,
        credentials: GatewayCredentials,
        session: SessionState,
    ) -> Sequence[Account]:
        ...

    def fetch_balance(
        self,
        credentials: GatewayCredentials,
        session: SessionState,
        account: Account,
    ) -> BalanceSnapshot:
        ...

    def fetch_transactions(
        self,
        credentials: GatewayCredentials,
        session: SessionState,
        account: Account,
        start_date: date | None,
        end_date: date | None,
    ) -> TransactionFeed:
        ...
