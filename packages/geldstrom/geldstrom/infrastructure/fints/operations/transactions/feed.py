"""Shared helpers for building domain TransactionFeed objects."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from geldstrom.domain import TransactionEntry, TransactionFeed


def build_feed(
    account_id: str,
    entries: Sequence[TransactionEntry],
    *,
    has_more: bool = False,
) -> TransactionFeed:
    """Build a TransactionFeed from a list of TransactionEntry objects."""
    if entries:
        start_date = min(entry.booking_date for entry in entries)
        end_date = max(entry.booking_date for entry in entries)
    else:
        today = date.today()
        start_date = end_date = today

    return TransactionFeed(
        account_id=account_id,
        entries=tuple(entries),
        start_date=start_date,
        end_date=end_date,
        has_more=has_more,
    )


def empty_feed(account_id: str) -> TransactionFeed:
    """Build an empty TransactionFeed for a given account."""
    today = date.today()
    return TransactionFeed(
        account_id=account_id,
        entries=(),
        start_date=today,
        end_date=today,
    )
