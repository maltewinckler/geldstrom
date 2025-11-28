"""FinTS 3.0 implementation of StatementPort."""
from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Sequence

from fints.application.ports import GatewayCredentials
from fints.domain import StatementDocument, StatementReference
from fints.domain.ports.statements import StatementPort
from fints.formals import StatementFormat
from fints.infrastructure.fints.session import FinTSSessionState

if TYPE_CHECKING:
    from fints.client import FinTS3PinTanClient
    from fints.models import SEPAAccount


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
        client = self._build_client(state)

        with self._logged_in(client):
            sepa_account = self._locate_sepa_account(client, account_id)
            raw_statements = client.get_statements(sepa_account)

        return self._parse_statement_list(account_id, raw_statements)

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
        client = self._build_client(state)

        with self._logged_in(client):
            sepa_account = self._locate_sepa_account(client, reference.account_id)

            # Determine format from preference
            fmt = self._format_from_mime(preferred_mime_type)

            raw_statement = client.get_statement(
                sepa_account,
                number=reference.statement_number,
                year=reference.year,
                format=fmt,
            )

        return self._parse_statement_document(reference, raw_statement)

    # --- Internal helpers ---

    def _build_client(
        self,
        state: FinTSSessionState,
    ) -> "FinTS3PinTanClient":
        """Build a configured FinTS client from session state."""
        from fints.client import FinTS3PinTanClient

        creds = self._credentials
        kwargs: dict[str, Any] = {
            "bank_identifier": creds.route.bank_code,
            "user_id": creds.user_id,
            "pin": creds.pin,
            "server": creds.server_url,
            "customer_id": creds.customer_id or creds.user_id,
            "product_id": creds.product_id,
            "product_version": creds.product_version,
            "tan_medium": creds.tan_medium,
            "from_data": state.client_blob,
            "system_id": state.system_id,
        }

        client = FinTS3PinTanClient(**kwargs)

        if creds.tan_method:
            client.set_tan_mechanism(creds.tan_method)

        return client

    @contextmanager
    def _logged_in(self, client: "FinTS3PinTanClient"):
        """Context manager for client login/logout."""
        with client:
            yield client

    @staticmethod
    def _account_key(account: "SEPAAccount") -> str:
        """Create lookup key from SEPA account."""
        return f"{account.accountnumber}:{account.subaccount or '0'}"

    def _locate_sepa_account(
        self,
        client: "FinTS3PinTanClient",
        account_id: str,
    ) -> "SEPAAccount":
        """Find SEPA account by account_id."""
        for sepa in client.get_sepa_accounts():
            if self._account_key(sepa) == account_id:
                return sepa
        raise ValueError(f"Account {account_id} not available from bank")

    def _parse_statement_list(
        self,
        account_id: str,
        raw_statements: Sequence,
    ) -> Sequence[StatementReference]:
        """Convert raw statement list to StatementReference objects."""
        references: list[StatementReference] = []

        for raw in raw_statements:
            # Extract statement metadata from raw response
            number = getattr(raw, "statement_number", None)
            year = getattr(raw, "year", None)
            date = getattr(raw, "date", None)

            if number is None or year is None:
                continue

            ref = StatementReference(
                account_id=account_id,
                statement_number=int(number),
                year=int(year),
                date=date,
                available_formats=self._extract_formats(raw),
            )
            references.append(ref)

        return tuple(references)

    @staticmethod
    def _extract_formats(raw) -> tuple[str, ...]:
        """Extract available formats from raw statement info."""
        formats: list[str] = []

        # Check for PDF availability
        if getattr(raw, "pdf_available", False):
            formats.append("application/pdf")

        # Check for MT940 availability
        if getattr(raw, "mt940_available", True):  # Usually available
            formats.append("application/x-mt940")

        return tuple(formats) if formats else ("application/x-mt940",)

    def _parse_statement_document(
        self,
        reference: StatementReference,
        raw_statement,
    ) -> StatementDocument:
        """Convert raw statement to StatementDocument."""
        content = getattr(raw_statement, "content", b"")
        if isinstance(content, str):
            content = content.encode("utf-8")

        # Determine MIME type from content or format
        mime_type = self._detect_mime_type(content)

        return StatementDocument(
            reference=reference,
            mime_type=mime_type,
            content=content,
        )

    @staticmethod
    def _detect_mime_type(content: bytes) -> str:
        """Detect MIME type from content."""
        if content.startswith(b"%PDF"):
            return "application/pdf"
        if content.startswith(b":20:") or b"\n:20:" in content[:100]:
            return "application/x-mt940"
        return "application/octet-stream"

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

