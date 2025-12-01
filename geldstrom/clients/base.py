"""Base types and protocols for FinTS clients.

This module defines common interfaces and data types used by all client
implementations in the package.
"""
from __future__ import annotations

from dataclasses import dataclass
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
class ClientCredentials:
    """
    All credentials needed to connect to a bank.

    This combines domain-level authentication (user/PIN) with
    infrastructure-specific details (server URL, product registration).

    Example:
        creds = ClientCredentials(
            route=BankRoute("DE", "12345678"),
            server_url="https://banking.example.com/fints",
            credentials=BankCredentials(
                user_id="user123",
                secret="mypin",
            ),
            product_id="MYPRODUCT123",
        )
    """

    route: BankRoute
    server_url: str
    credentials: BankCredentials
    product_id: str
    product_version: str = "1.0"

    @property
    def user_id(self) -> str:
        """Convenience accessor for credentials.user_id."""
        return self.credentials.user_id

    @property
    def pin(self) -> str:
        """Convenience accessor for credentials.secret (unmasked)."""
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


class BankClient(Protocol):
    """
    Protocol defining the minimal interface for a bank client.

    All client implementations should satisfy this protocol.
    """

    def connect(self) -> Sequence[Account]:
        """Establish connection and fetch account list."""
        ...

    def list_accounts(self) -> Sequence[Account]:
        """Return available accounts (may trigger connect if needed)."""
        ...

    @property
    def session_state(self) -> SessionToken | None:
        """Current session state for persistence."""
        ...

    @property
    def capabilities(self) -> BankCapabilities | None:
        """Bank's advertised capabilities."""
        ...


class ReadOnlyBankClient(BankClient, Protocol):
    """Protocol for read-only bank clients."""

    def get_balance(self, account_id: str) -> BalanceSnapshot:
        """Fetch current balance for an account."""
        ...

    def get_transactions(
        self,
        account_id: str,
        start_date=None,
        end_date=None,
    ) -> TransactionFeed:
        """Fetch transaction history for an account."""
        ...


__all__ = [
    "BankClient",
    "ClientCredentials",
    "ReadOnlyBankClient",
]

