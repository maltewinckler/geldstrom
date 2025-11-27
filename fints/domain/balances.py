"""Value objects describing balances."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class BalanceAmount:
    amount: Decimal
    currency: str


@dataclass(frozen=True)
class BalanceSnapshot:
    account_id: str
    as_of: datetime
    booked: BalanceAmount
    available: Optional[BalanceAmount] = None
    credit_limit: Optional[BalanceAmount] = None
