"""Base types and protocols for FinTS clients.

This module defines the interface that all FinTS client implementations
should satisfy.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Protocol

from geldstrom.domain import (
    Account,
    BalanceSnapshot,
    BankCapabilities,
    SessionToken,
    TransactionFeed,
)
from geldstrom.domain.model.tan import TANMethod


class BankClient(Protocol):
    """
    Protocol defining the interface for a bank client.

    All client implementations should satisfy this protocol.
    `FinTS3Client` is the primary implementation.
    """

    def connect(self) -> Sequence[Account]:
        """Establish connection and fetch account list."""
        ...

    def disconnect(self) -> None:
        """Close the session."""
        ...

    def list_accounts(self) -> Sequence[Account]:
        """Return available accounts (may trigger connect if needed)."""
        ...

    def get_balance(self, account: Account | str) -> BalanceSnapshot:
        """Fetch current balance for an account."""
        ...

    def get_transactions(
        self,
        account: Account | str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> TransactionFeed:
        """Fetch transaction history for an account."""
        ...

    def get_tan_methods(self) -> Sequence[TANMethod]:
        """Get available TAN authentication methods."""
        ...

    @property
    def session_state(self) -> SessionToken | None:
        """Current session state for persistence."""
        ...

    @property
    def capabilities(self) -> BankCapabilities | None:
        """Bank's advertised capabilities."""
        ...

    @property
    def is_connected(self) -> bool:
        """Whether the client is currently connected."""
        ...


__all__ = [
    "BankClient",
]
