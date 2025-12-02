"""Transaction history operations for FinTS.

This module handles HKKAZ (MT940) and HKCAZ (CAMT) segment exchanges
for fetching account transaction history with pagination support.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING

from geldstrom.infrastructure.fints.protocol import (
    HKCAZ1,
    HKKAZ5,
    HKKAZ6,
    HKKAZ7,
    SupportedMessageTypes,
)
from geldstrom.infrastructure.fints.protocol.formals import SEPAAccount
from geldstrom.utils import mt940_to_array

from .helpers import build_account_field, find_highest_supported_version
from .pagination import TouchdownPaginator

if TYPE_CHECKING:
    from geldstrom.infrastructure.fints.dialog import Dialog
    from geldstrom.infrastructure.fints.protocol import ParameterStore

logger = logging.getLogger(__name__)


# Supported segment versions
SUPPORTED_HKKAZ = (HKKAZ7, HKKAZ6, HKKAZ5)
SUPPORTED_HKCAZ = (HKCAZ1,)


@dataclass
class MT940TransactionResult:
    """Result of an MT940 transaction fetch."""

    transactions: list  # List of mt940.models.Transaction
    pages_fetched: int = 1
    has_more: bool = False


@dataclass
class CAMTTransactionResult:
    """Result of a CAMT transaction fetch."""

    booked_documents: list[bytes] = field(default_factory=list)
    pending_documents: list[bytes] = field(default_factory=list)
    pages_fetched: int = 1
    has_more: bool = False


class TransactionOperations:
    """
    Handles transaction history operations.

    This class provides methods to:
    - Fetch MT940 transactions via HKKAZ
    - Fetch CAMT XML transactions via HKCAZ

    Usage:
        ops = TransactionOperations(dialog, parameters)
        result = ops.fetch_mt940(account, start_date, end_date)
    """

    def __init__(
        self,
        dialog: Dialog,
        parameters: ParameterStore,
        max_pages: int = 100,
    ) -> None:
        """
        Initialize transaction operations.

        Args:
            dialog: Active dialog for sending requests
            parameters: Parameter store with BPD
            max_pages: Maximum pages to fetch in pagination
        """
        self._dialog = dialog
        self._parameters = parameters
        self._paginator = TouchdownPaginator(dialog, max_pages=max_pages)

    def fetch_mt940(
        self,
        account: SEPAAccount,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> MT940TransactionResult:
        """
        Fetch transaction history in MT940 format.

        Args:
            account: SEPA account to query
            start_date: Start of date range (optional)
            end_date: End of date range (optional)

        Returns:
            MT940TransactionResult with parsed transactions

        Raises:
            FinTSUnsupportedOperation: If bank doesn't support HKKAZ
        """
        logger.info(
            "Fetching MT940 transactions for %s from %s to %s",
            account.iban or account.accountnumber,
            start_date,
            end_date,
        )

        # Find highest supported HKKAZ version
        hkkaz_class = find_highest_supported_version(
            self._parameters.bpd.segments,
            SUPPORTED_HKKAZ,
            raise_if_missing="Bank does not support transaction queries (HKKAZ)",
        )

        # Build account field
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

        # Fetch with pagination
        result = self._paginator.fetch(
            segment_factory=segment_factory,
            response_type="HIKAZ",
            extract_items=extract_mt940,
        )

        # Combine and parse MT940
        mt940_segments = [s for s in result.items if s]
        combined = self._decode_mt940_segments(mt940_segments)
        transactions = mt940_to_array(combined)

        return MT940TransactionResult(
            transactions=transactions,
            pages_fetched=result.pages_fetched,
            has_more=result.has_more,
        )

    def fetch_camt(
        self,
        account: SEPAAccount,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> CAMTTransactionResult:
        """
        Fetch transaction history in CAMT XML format.

        Args:
            account: SEPA account to query
            start_date: Start of date range (optional)
            end_date: End of date range (optional)

        Returns:
            CAMTTransactionResult with raw XML documents

        Raises:
            FinTSUnsupportedOperation: If bank doesn't support HKCAZ
        """
        logger.info(
            "Fetching CAMT transactions for %s from %s to %s",
            account.iban or account.accountnumber,
            start_date,
            end_date,
        )

        # Find highest supported HKCAZ version
        hkcaz_class = find_highest_supported_version(
            self._parameters.bpd.segments,
            SUPPORTED_HKCAZ,
            raise_if_missing="Bank does not support CAMT queries (HKCAZ)",
        )

        # Get supported CAMT message types from BPD
        camt_messages = self._get_supported_camt_types()
        if not camt_messages:
            camt_messages = ("urn:iso:std:iso:20022:tech:xsd:camt.052.001.02",)

        # HKCAZ expects SupportedMessageTypes DEG
        supported_messages = SupportedMessageTypes(expected_type=list(camt_messages))

        # Build account field
        account_field = build_account_field(hkcaz_class, account)

        booked_docs: list[bytes] = []
        pending_docs: list[bytes] = []

        def segment_factory(touchdown: str | None):
            return hkcaz_class(
                account=account_field,
                supported_camt_messages=supported_messages,
                all_accounts=False,
                date_start=start_date,
                date_end=end_date,
                max_number_responses=None,
                touchdown_point=touchdown,
            )

        def extract_camt(seg) -> tuple[list[bytes], bytes | None] | None:
            booked = []
            pending = None
            stmt = getattr(seg, "statement_booked", None)
            if stmt and hasattr(stmt, "camt_statements"):
                booked = list(stmt.camt_statements)
            if hasattr(seg, "statement_pending"):
                pending = seg.statement_pending
            return (booked, pending) if booked or pending else None

        # Fetch with pagination
        result = self._paginator.fetch(
            segment_factory=segment_factory,
            response_type="HICAZ",
            extract_items=extract_camt,
        )

        # Flatten results
        for item in result.items:
            if item:
                booked, pending = item
                booked_docs.extend(booked)
                if pending:
                    pending_docs.append(pending)

        return CAMTTransactionResult(
            booked_documents=booked_docs,
            pending_documents=pending_docs,
            pages_fetched=result.pages_fetched,
            has_more=result.has_more,
        )

    def _decode_mt940_segments(self, segments: Sequence[bytes]) -> str:
        """Decode MT940 segments into a single string for parsing."""
        parts = []
        for seg in segments:
            if isinstance(seg, bytes):
                parts.append(seg.decode("iso-8859-1"))
            else:
                parts.append(str(seg))
        return "".join(parts)

    def _get_supported_camt_types(self) -> tuple[str, ...]:
        """Get supported CAMT message types from BPD."""
        segment = self._parameters.bpd.find_segment("HICAZS")
        if not segment:
            return ()

        identifiers: list[str] = []
        self._collect_camt_identifiers(segment, identifiers)

        # Deduplicate while preserving order
        seen: set[str] = set()
        ordered: list[str] = []
        for ident in identifiers:
            if ident not in seen:
                seen.add(ident)
                ordered.append(ident)

        return tuple(ordered)

    def _collect_camt_identifiers(self, node, bucket: list[str]) -> None:
        """Recursively collect CAMT URN identifiers from a segment."""
        if node is None:
            return

        if isinstance(node, str):
            if "camt." in node.lower():
                bucket.append(node)
            return

        if isinstance(node, (bytes, bytearray)):
            return

        if isinstance(node, Iterable) and not isinstance(node, str):
            for item in node:
                self._collect_camt_identifiers(item, bucket)
            return

        # Check Pydantic model fields
        model_fields = getattr(node, "model_fields", None)
        if model_fields:
            for name in model_fields:
                self._collect_camt_identifiers(getattr(node, name, None), bucket)
