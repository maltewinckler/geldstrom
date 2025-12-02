"""FinTS 3.0 implementation of StatementPort."""
from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import TYPE_CHECKING

from geldstrom.infrastructure.fints.credentials import GatewayCredentials
from geldstrom.domain import StatementDocument, StatementReference
from geldstrom.domain.ports.statements import StatementPort
from geldstrom.infrastructure.fints.protocol import StatementFormat
from geldstrom.infrastructure.fints.session import FinTSSessionState

from .connection import FinTSConnectionHelper
from .helpers import locate_sepa_account

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class FinTSStatementAdapter(StatementPort):
    """
    FinTS 3.0 implementation of StatementPort.

    Fetches archived account statements via HKEKA segments.
    """

    def __init__(self, credentials: GatewayCredentials) -> None:
        """
        Initialize with credentials.

        Args:
            credentials: Bank connection credentials
        """
        self._credentials = credentials

    def list_statements(
        self,
        state: FinTSSessionState,
        account_id: str,
    ) -> Sequence[StatementReference]:
        """
        List available statements for an account.

        Args:
            state: Current session state
            account_id: Account identifier

        Returns:
            Sequence of StatementReference for available statements
        """
        from geldstrom.infrastructure.fints.operations import (
            AccountOperations,
            StatementOperations,
        )

        helper = FinTSConnectionHelper(self._credentials)

        with helper.connect(state) as ctx:
            account_ops = AccountOperations(ctx.dialog, ctx.parameters)
            stmt_ops = StatementOperations(ctx.dialog, ctx.parameters)

            # Find SEPA account
            sepa_account = locate_sepa_account(account_ops, account_id)

            # List statements
            result = stmt_ops.list_statements(sepa_account)

            # Convert to domain objects
            return self._references_from_operations(account_id, result.statements)

    def fetch_statement(
        self,
        state: FinTSSessionState,
        reference: StatementReference,
        *,
        preferred_mime_type: str | None = None,
    ) -> StatementDocument:
        """
        Fetch a specific statement document.

        Args:
            state: Current session state
            reference: Reference to the statement to fetch
            preferred_mime_type: Preferred format (e.g., "application/pdf")

        Returns:
            StatementDocument with content
        """
        from geldstrom.infrastructure.fints.operations import (
            AccountOperations,
            StatementOperations,
        )

        helper = FinTSConnectionHelper(self._credentials)

        with helper.connect(state) as ctx:
            account_ops = AccountOperations(ctx.dialog, ctx.parameters)
            stmt_ops = StatementOperations(ctx.dialog, ctx.parameters)

            # Find SEPA account
            sepa_account = locate_sepa_account(account_ops, reference.account_id)

            # Determine format
            fmt = self._format_from_mime(preferred_mime_type)

            # Fetch statement
            result = stmt_ops.fetch_statement(
                sepa_account,
                number=reference.statement_number,
                year=reference.year,
                format=fmt,
            )

            # Convert to domain object
            return StatementDocument(
                reference=reference,
                mime_type=result.mime_type,
                content=result.content or b"",
            )

    # --- Helpers ---

    def _references_from_operations(
        self,
        account_id: str,
        statements,
    ) -> Sequence[StatementReference]:
        """Convert operations result to StatementReference objects."""
        from geldstrom.infrastructure.fints.operations import StatementInfo

        references: list[StatementReference] = []

        for stmt in statements:
            if not isinstance(stmt, StatementInfo):
                continue

            ref = StatementReference(
                account_id=account_id,
                statement_number=stmt.number,
                year=stmt.year,
                date=stmt.date_created,
                available_formats=("application/pdf", "application/x-mt940"),
            )
            references.append(ref)

        return tuple(references)

    @staticmethod
    def _format_from_mime(mime_type: str | None) -> StatementFormat | None:
        """Convert MIME type to FinTS StatementFormat."""
        if not mime_type:
            return None
        if "pdf" in mime_type.lower():
            return StatementFormat.PDF
        if "mt940" in mime_type.lower():
            return StatementFormat.MT940
        return None


__all__ = ["FinTSStatementAdapter"]
