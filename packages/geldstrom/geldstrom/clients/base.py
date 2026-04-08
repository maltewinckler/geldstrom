"""Base types and protocols for FinTS clients."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Protocol

from geldstrom.domain import (
    Account,
    BalanceSnapshot,
    BankCapabilities,
    TransactionFeed,
)
from geldstrom.infrastructure.fints.session import SessionToken
from geldstrom.infrastructure.fints.tan import TANMethod


class BankClient(Protocol):
    """Protocol defining the interface for a bank client."""

    def connect(self) -> Sequence[Account]: ...
    def disconnect(self) -> None: ...
    def list_accounts(self) -> Sequence[Account]: ...
    def get_balance(self, account: Account | str) -> BalanceSnapshot: ...
    def get_transactions(
        self,
        account: Account | str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> TransactionFeed: ...
    def get_tan_methods(self) -> Sequence[TANMethod]: ...

    @property
    def session_state(self) -> SessionToken | None: ...

    @property
    def capabilities(self) -> BankCapabilities | None: ...

    @property
    def is_connected(self) -> bool: ...


__all__ = [
    "BankClient",
]
