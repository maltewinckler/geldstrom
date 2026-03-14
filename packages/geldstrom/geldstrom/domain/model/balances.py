"""Value objects describing balances."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class BalanceAmount(BaseModel, frozen=True):
    amount: Decimal
    currency: str


class BalanceSnapshot(BaseModel, frozen=True):
    """
    Snapshot of account balance at a point in time.

    Attributes:
        account_id: Identifier of the account
        as_of: Timestamp when the balance was recorded
        booked: The booked (confirmed) balance
        pending: The pending (unconfirmed) balance, if available
        available: The available balance (may differ from booked due to holds)
        credit_limit: The credit limit on the account, if applicable
    """

    account_id: str
    as_of: datetime
    booked: BalanceAmount
    pending: BalanceAmount | None = None
    available: BalanceAmount | None = None
    credit_limit: BalanceAmount | None = None
