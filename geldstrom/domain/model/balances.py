"""Value objects describing balances."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class BalanceAmount(BaseModel, frozen=True):
    amount: Decimal
    currency: str


class BalanceSnapshot(BaseModel, frozen=True):
    account_id: str
    as_of: datetime
    booked: BalanceAmount
    available: BalanceAmount | None = None
    credit_limit: BalanceAmount | None = None
