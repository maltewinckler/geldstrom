"""Balance retrieval port."""
from __future__ import annotations

from typing import Protocol, Sequence

from fints.domain import BalanceSnapshot, SessionToken


class BalancePort(Protocol):
    """Expose current balances supported by the active session."""

    def fetch_balances(
        self,
        state: SessionToken,
        account_ids: Sequence[str] | None = None,
    ) -> Sequence[BalanceSnapshot]:
        raise NotImplementedError
