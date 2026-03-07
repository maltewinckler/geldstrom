"""Transaction value objects.

Value Objects: immutable, identity by value, no lifecycle.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


# Value Object — identity by (start, end)
class DateRange(BaseModel, frozen=True):
    """Inclusive date range for a transaction query."""

    start: date
    end: date


# Value Object — identity by (iban, date_range)
class TransactionFetch(BaseModel, frozen=True):
    """Parameters for a transaction fetch request."""

    iban: str
    date_range: DateRange


# Value Object — identity by entry_id
class TransactionData(BaseModel, frozen=True):
    """A single bank transaction.

    Field names mirror geldstrom's TransactionEntry for consistency.
    Value Object: immutable once received from the bank.
    """

    entry_id: str
    booking_date: date
    value_date: date
    amount: Decimal
    currency: str
    purpose: str
    counterpart_name: str | None = None
    counterpart_iban: str | None = None
    metadata: dict[str, str] = {}
