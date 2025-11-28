"""FinTS-specific statement operations."""
from __future__ import annotations

from typing import TYPE_CHECKING

from fints.formals import StatementFormat
from fints.models import SEPAAccount
from fints.segments.statement import HKKAU1, HKKAU2, HKEKA3, HKEKA4, HKEKA5

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from fints.client import FinTS3Client


class StatementsService:
    """Encapsulates statement queries available via FinTS."""

    def __init__(self, client: "FinTS3Client") -> None:
        self._client = client

    def list_statements(self, account: SEPAAccount):
        client = self._client
        with client._get_dialog() as dialog:  # noqa: SLF001 - legacy adapter
            hkkau = client._find_highest_supported_command(HKKAU1, HKKAU2)
            responses = client._fetch_with_touchdowns(
                dialog,
                lambda touchdown: hkkau(
                    account=hkkau._fields['account'].type.from_sepa_account(account),
                    touchdown_point=touchdown,
                ),
                lambda response: response,
                'HIKAU',
            )
        return responses

    def fetch_statement(
        self,
        account: SEPAAccount,
        number: int,
        year: int,
        *,
        format: StatementFormat | None = None,
    ):
        client = self._client
        with client._get_dialog() as dialog:  # noqa: SLF001 - legacy adapter
            hkeka = client._find_highest_supported_command(HKEKA3, HKEKA4, HKEKA5)
            seg = hkeka(
                account=hkeka._fields['account'].type.from_sepa_account(account),
                statement_format=format,
                statement_number=number,
                statement_year=year,
            )
            response = client._send_with_possible_retry(  # noqa: SLF001
                dialog,
                seg,
                self._extract_statement,
            )
        return response

    @staticmethod
    def _extract_statement(command_seg, response):
        for resp in response.response_segments(command_seg, 'HIEKA'):
            return resp
        return None
