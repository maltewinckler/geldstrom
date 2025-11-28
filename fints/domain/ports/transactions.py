"""Port describing how to fetch transaction history."""
from __future__ import annotations

from datetime import date
from typing import Protocol

from fints.domain import SessionToken, TransactionFeed


class TransactionHistoryPort(Protocol):
    """Provide structured transactions across various connectors."""

    def fetch_history(
        self,
        state: SessionToken,
        account_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        *,
        include_pending: bool = False,
    ) -> TransactionFeed:
        raise NotImplementedError
