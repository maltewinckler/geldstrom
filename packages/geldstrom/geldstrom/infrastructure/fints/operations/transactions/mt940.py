"""MT940 transaction pipeline: HKKAZ → decode → parse → TransactionEntry → TransactionFeed.

This module provides the complete data flow for MT940 transaction history:
1. Construct HKKAZ segments with version negotiation
2. Paginate via TouchdownPaginator
3. Decode MT940 byte segments
4. Parse via mt940 library
5. Convert to domain TransactionEntry/TransactionFeed models
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

import mt940 as mt940_lib

from geldstrom.domain import TransactionEntry, TransactionFeed
from geldstrom.infrastructure.fints.protocol import HKKAZ5, HKKAZ6, HKKAZ7
from geldstrom.infrastructure.fints.protocol.formals import SEPAAccount

from ..helpers import build_account_field, find_highest_supported_version
from ..pagination import TouchdownPaginator
from .feed import build_feed, empty_feed

if TYPE_CHECKING:
    from geldstrom.infrastructure.fints.dialog import Dialog, ProcessedResponse
    from geldstrom.infrastructure.fints.protocol import ParameterStore

logger = logging.getLogger(__name__)

SUPPORTED_HKKAZ = (HKKAZ7, HKKAZ6, HKKAZ5)


# ---------------------------------------------------------------------------
# Parsing utilities
# ---------------------------------------------------------------------------


def mt940_to_array(data: str):
    """Parse MT940 data into transaction objects."""
    data = data.replace("@@", "\r\n")
    data = data.replace("-0000", "+0000")
    transactions = mt940_lib.models.Transactions()
    return transactions.parse(data)


# ---------------------------------------------------------------------------
# Fetcher - segments -> domain models
# ---------------------------------------------------------------------------


class Mt940Fetcher:
    """Fetches MT940 transactions via HKKAZ and converts to domain models."""

    def __init__(
        self,
        dialog: Dialog,
        parameters: ParameterStore,
        max_pages: int = 100,
    ) -> None:
        self._dialog = dialog
        self._parameters = parameters
        self._paginator = TouchdownPaginator(dialog, max_pages=max_pages)

    def fetch(
        self,
        account: SEPAAccount,
        account_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        *,
        initial_touchdown: str | None = None,
    ) -> TransactionFeed:
        """Fetch MT940 transactions and return a domain TransactionFeed.

        When *initial_touchdown* is provided the fetcher resumes pagination
        from that point (e.g. after a TAN approval delivered the first page).
        """
        logger.debug(
            "Fetching MT940 transactions for %s from %s to %s (touchdown=%s)",
            account.iban or account.accountnumber,
            start_date,
            end_date,
            initial_touchdown,
        )

        hkkaz_class = find_highest_supported_version(
            self._parameters.bpd.segments,
            SUPPORTED_HKKAZ,
            raise_if_missing="Bank does not support transaction queries (HKKAZ)",
        )
        account_field = build_account_field(hkkaz_class, account)

        def segment_factory(touchdown: str | None):
            return hkkaz_class(
                account=account_field,
                all_accounts=False,
                date_start=start_date,
                date_end=end_date,
                touchdown_point=touchdown,
            )

        def extract_mt940(seg) -> bytes | None:
            return getattr(seg, "statement_booked", None)

        result = self._paginator.fetch(
            segment_factory=segment_factory,
            response_type="HIKAZ",
            extract_items=extract_mt940,
            initial_touchdown=initial_touchdown,
        )
        mt940_segments = [s for s in result.items if s]
        combined = _decode_mt940_segments(mt940_segments)
        raw_transactions = mt940_to_array(combined)

        return _transactions_to_feed(
            account_id, raw_transactions, has_more=result.has_more
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _decode_mt940_segments(segments: Sequence[bytes]) -> str:
    """Decode MT940 segments into a single string for parsing."""
    parts = []
    for seg in segments:
        if isinstance(seg, bytes):
            parts.append(seg.decode("iso-8859-1"))
        else:
            parts.append(str(seg))
    return "".join(parts)


def _transactions_to_feed(
    account_id: str,
    raw_transactions: Iterable,
    *,
    has_more: bool = False,
) -> TransactionFeed:
    """Convert raw MT940 transaction objects to a domain TransactionFeed."""
    entries = [
        _mt940_to_entry(account_id, idx, tx) for idx, tx in enumerate(raw_transactions)
    ]
    return build_feed(account_id, entries, has_more=has_more)


def _mt940_to_entry(
    account_id: str,
    idx: int,
    tx,
) -> TransactionEntry:
    """Convert a single mt940.Transaction to a domain TransactionEntry."""
    if logger.isEnabledFor(logging.DEBUG):
        _log_mt940_fields(tx, idx)

    amount = tx.data.get("amount")
    value = Decimal(str(getattr(amount, "amount", "0")))
    currency = getattr(amount, "currency", "EUR")

    booking_date = tx.data.get("date") or tx.data.get("entry_date") or date.today()
    value_date = tx.data.get("entry_date") or booking_date

    purpose = tx.data.get("purpose")
    if isinstance(purpose, list):
        purpose_text = " ".join(str(p) for p in purpose if p)
    else:
        purpose_text = str(purpose or "")

    counterpart = tx.data.get("applicant_name") or tx.data.get("beneficiary")
    counterpart_iban = tx.data.get("applicant_iban")
    entry_id = tx.data.get("transaction_reference") or f"{account_id}-{idx}"

    return TransactionEntry(
        entry_id=entry_id,
        booking_date=booking_date,
        value_date=value_date,
        amount=value,
        currency=currency,
        purpose=purpose_text,
        counterpart_name=counterpart,
        counterpart_iban=counterpart_iban,
    )


def parse_approved_response(
    response: ProcessedResponse,
    account_id: str,
) -> TransactionFeed:
    """Parse MT940 data from a post-TAN-approval ProcessedResponse."""
    if response.raw_response is None:
        return empty_feed(account_id)
    segments = [
        getattr(seg, "statement_booked", None)
        for seg in response.raw_response.find_segments("HIKAZ")
    ]
    segments = [s for s in segments if s]
    if not segments:
        return empty_feed(account_id)
    combined = _decode_mt940_segments(segments)
    raw_transactions = mt940_to_array(combined)
    return _transactions_to_feed(account_id, raw_transactions)


def _log_mt940_fields(tx, idx: int) -> None:
    logger.debug("MT940 Transaction #%d - Available fields:", idx)
    for key, value in tx.data.items():
        value_str = str(value)
        if len(value_str) > 100:
            value_str = value_str[:100] + "..."
        logger.debug("  %s: %s", key, value_str)
