"""Transaction feed abstractions."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Mapping, Sequence


@dataclass(frozen=True)
class TransactionEntry:
    entry_id: str
    booking_date: date
    value_date: date
    amount: Decimal
    currency: str
    purpose: str
    counterpart_name: str | None = None
    counterpart_iban: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class TransactionFeed:
    account_id: str
    entries: Sequence[TransactionEntry]
    start_date: date
    end_date: date
    has_more: bool = False
