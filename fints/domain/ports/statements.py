"""Statement archive port."""
from __future__ import annotations

from typing import Protocol, Sequence

from fints.domain import SessionToken, StatementDocument, StatementReference


class StatementPort(Protocol):
    """Query stored statements for a bank account."""

    def list_statements(
        self,
        state: SessionToken,
        account_id: str,
    ) -> Sequence[StatementReference]:
        raise NotImplementedError

    def fetch_statement(
        self,
        state: SessionToken,
        reference: StatementReference,
        *,
        preferred_mime_type: str | None = None,
    ) -> StatementDocument:
        raise NotImplementedError
