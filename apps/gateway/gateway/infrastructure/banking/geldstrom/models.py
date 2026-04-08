"""Gateway-owned Geldstrom anti-corruption models."""

from __future__ import annotations

from datetime import date
from typing import Protocol

from geldstrom.domain import Account, BalanceSnapshot, TransactionFeed
from geldstrom.infrastructure.fints.credentials import GatewayCredentials
from geldstrom.infrastructure.fints.session import FinTSSessionState, SessionToken
from geldstrom.infrastructure.fints.tan import TANMethod as GeldstromTanMethod


class GeldstromClient(Protocol):
    """Minimal Geldstrom client surface the gateway depends on."""

    def list_accounts(self) -> list[Account]: ...

    def get_balances(self) -> list[BalanceSnapshot]: ...

    def get_transactions(
        self,
        account: Account | str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> TransactionFeed: ...

    def get_tan_methods(self) -> list[GeldstromTanMethod]: ...

    @property
    def session_state(self) -> SessionToken | None: ...


class GeldstromClientFactory(Protocol):
    """Factory for concrete Geldstrom clients."""

    def create(
        self,
        credentials: GatewayCredentials,
        session_state: FinTSSessionState | None = None,
    ) -> GeldstromClient: ...
