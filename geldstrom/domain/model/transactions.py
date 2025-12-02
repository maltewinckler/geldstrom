"""Transaction feed abstractions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class TransactionEntry(BaseModel, frozen=True):
    entry_id: str
    booking_date: date
    value_date: date
    amount: Decimal
    currency: str
    purpose: str
    counterpart_name: str | None = None
    counterpart_iban: str | None = None
    metadata: Mapping[str, str] = {}


class TransactionFeed(BaseModel, frozen=True):
    account_id: str
    entries: Sequence[TransactionEntry]
    start_date: date
    end_date: date
    has_more: bool = False
