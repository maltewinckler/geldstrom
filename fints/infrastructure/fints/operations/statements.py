"""Statement retrieval operations for FinTS.

This module handles HKEKA segment exchanges for listing and fetching
account statements (Kontoauszüge).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, time
from typing import TYPE_CHECKING, Sequence

from fints.exceptions import FinTSUnsupportedOperation
from fints.infrastructure.fints.protocol import (
    Confirmation,
    StatementFormat,
    HIEKA3,
    HIEKA4,
    HIEKA5,
    HKEKA3,
    HKEKA4,
    HKEKA5,
)
from fints.models import SEPAAccount

from .pagination import TouchdownPaginator, find_highest_supported_version

if TYPE_CHECKING:
    from fints.infrastructure.fints.dialog import Dialog
    from fints.infrastructure.fints.protocol import ParameterStore

logger = logging.getLogger(__name__)


# Supported segment versions
SUPPORTED_HKEKA = (HKEKA5, HKEKA4, HKEKA3)
SUPPORTED_HIEKA = {
    5: HIEKA5,
    4: HIEKA4,
    3: HIEKA3,
}


@dataclass
class StatementInfo:
    """Information about an available statement."""

    number: int
    year: int
    date_created: date | None = None
    time_created: time | None = None
    is_available: bool = True
    creation_type: str | None = None


@dataclass
class StatementDocument:
    """A fetched statement document."""

    number: int
    year: int
    format: StatementFormat | None = None
    content: bytes | None = None
    mime_type: str = "application/pdf"


@dataclass
class StatementListResult:
    """Result of listing available statements."""

    statements: list[StatementInfo]
    pages_fetched: int = 1


class StatementOperations:
    """
    Handles statement (Kontoauszug) operations.

    This class provides methods to:
    - List available statements via HKEKA
    - Fetch individual statement documents

    Usage:
        ops = StatementOperations(dialog, parameters)
        available = ops.list_statements(account)
        doc = ops.fetch_statement(account, number=1, year=2024)
    """

    def __init__(
        self,
        dialog: "Dialog",
        parameters: "ParameterStore",
        max_pages: int = 100,
    ) -> None:
        """
        Initialize statement operations.

        Args:
            dialog: Active dialog for sending requests
            parameters: Parameter store with BPD
            max_pages: Maximum pages to fetch in pagination
        """
        self._dialog = dialog
        self._parameters = parameters
        self._paginator = TouchdownPaginator(dialog, max_pages=max_pages)

    def list_statements(self, account: SEPAAccount) -> StatementListResult:
        """
        List available statements for an account.

        Args:
            account: SEPA account to query

        Returns:
            StatementListResult with available statements

        Raises:
            FinTSUnsupportedOperation: If bank doesn't support HKEKA
        """
        logger.info(
            "Listing statements for account %s",
            account.iban or account.accountnumber,
        )

        # Find highest supported HKEKA version
        hkeka_class = find_highest_supported_version(
            self._parameters.bpd.segments,
            SUPPORTED_HKEKA,
        )

        if not hkeka_class:
            raise FinTSUnsupportedOperation(
                "Bank does not support statement queries (HKEKA)"
            )

        # Build account field
        from .helpers import get_account_type_for_segment
        account_type = get_account_type_for_segment(hkeka_class)
        account_field = account_type.from_sepa_account(account)

        statements: list[StatementInfo] = []

        def segment_factory(touchdown: str | None):
            return hkeka_class(
                account=account_field,
                statement_format=None,  # List all formats
                statement_number=0,  # 0 = list available
                statement_year=0,
                touchdown_point=touchdown,
            )

        def extract_statement_info(seg) -> StatementInfo | None:
            return StatementInfo(
                number=seg.statement_number,
                year=getattr(seg, "year", 0) or 0,
                date_created=getattr(seg, "date_created", None),
                time_created=getattr(seg, "time_created", None),
                is_available=seg.collection_possible == "J" if hasattr(seg, "collection_possible") else True,
                creation_type=getattr(seg, "creation_type", None),
            )

        # Fetch with pagination
        hieka_type = f"HIEKA"
        result = self._paginator.fetch(
            segment_factory=segment_factory,
            response_type=hieka_type,
            extract_items=extract_statement_info,
        )

        return StatementListResult(
            statements=list(result.items),
            pages_fetched=result.pages_fetched,
        )

    def fetch_statement(
        self,
        account: SEPAAccount,
        number: int,
        year: int,
        format: StatementFormat | None = None,
    ) -> StatementDocument:
        """
        Fetch a specific statement document.

        Args:
            account: SEPA account
            number: Statement number
            year: Statement year
            format: Desired format (PDF, MT940, etc.)

        Returns:
            StatementDocument with content

        Raises:
            FinTSUnsupportedOperation: If bank doesn't support HKEKA
            ValueError: If statement not found
        """
        logger.info(
            "Fetching statement %d/%d for account %s",
            number,
            year,
            account.iban or account.accountnumber,
        )

        # Find highest supported HKEKA version
        hkeka_class = find_highest_supported_version(
            self._parameters.bpd.segments,
            SUPPORTED_HKEKA,
        )

        if not hkeka_class:
            raise FinTSUnsupportedOperation(
                "Bank does not support statement queries (HKEKA)"
            )

        # Build account field
        from .helpers import get_account_type_for_segment
        account_type = get_account_type_for_segment(hkeka_class)
        account_field = account_type.from_sepa_account(account)

        # Send fetch request
        segment = hkeka_class(
            account=account_field,
            statement_format=format,
            statement_number=number,
            statement_year=year,
        )
        response = self._dialog.send(segment)

        # Extract document from response
        return self._extract_document(response, segment, hkeka_class.VERSION, number, year, format)

    def _extract_document(
        self,
        response,
        request_segment,
        version: int,
        number: int,
        year: int,
        format: StatementFormat | None,
    ) -> StatementDocument:
        """Extract statement document from response."""
        if response.raw_response is None:
            raise ValueError("No response received for statement query")

        hieka_type = "HIEKA"

        for seg in response.raw_response.response_segments(request_segment, hieka_type):
            # Check if this is the statement content (not just info)
            content = getattr(seg, "statement", None) or getattr(seg, "content", None)
            if content:
                return StatementDocument(
                    number=number,
                    year=year,
                    format=format,
                    content=content if isinstance(content, bytes) else content.encode(),
                    mime_type=self._get_mime_type(format),
                )

        raise ValueError(f"Statement {number}/{year} not found in response")

    def _get_mime_type(self, format: StatementFormat | None) -> str:
        """Get MIME type for statement format."""
        if format == StatementFormat.PDF:
            return "application/pdf"
        elif format == StatementFormat.MT940:
            return "text/plain"
        elif format == StatementFormat.ISO_XML:
            return "application/xml"
        return "application/octet-stream"

