"""FinTS-specific transaction operations."""
from __future__ import annotations

import logging
from datetime import date
from typing import TYPE_CHECKING, Iterable, Sequence

from fints.formals import SupportedMessageTypes
from fints.models import SEPAAccount
from fints.segments.statement import HKCAZ1, HKKAZ5, HKKAZ6, HKKAZ7
from fints.utils import mt940_to_array

if TYPE_CHECKING:  # pragma: no cover - import guard
    from fints.client import FinTS3Client

logger = logging.getLogger(__name__)


class TransactionsService:
    """Provides higher level read APIs for transaction history via FinTS."""

    def __init__(self, client: "FinTS3Client") -> None:
        self._client = client

    def fetch_mt940(
        self,
        account: SEPAAccount,
        start_date: date | None = None,
        end_date: date | None = None,
        *,
        include_pending: bool = False,
    ):
        client = self._client
        with client._get_dialog() as dialog:  # noqa: SLF001 - legacy adapter
            hkkaz = client._find_highest_supported_command(HKKAZ5, HKKAZ6, HKKAZ7)
            logger.info("Start fetching from %s to %s", start_date, end_date)
            response = client._fetch_with_touchdowns(
                dialog,
                lambda touchdown: hkkaz(
                    account=hkkaz._fields['account'].type.from_sepa_account(account),
                    all_accounts=False,
                    date_start=start_date,
                    date_end=end_date,
                    touchdown_point=touchdown,
                ),
                lambda responses: mt940_to_array(
                    ''.join(
                        self._mt940_segments(responses, include_pending)
                    )
                ),
                'HIKAZ',
            )
            logger.info('Fetching done.')
        return response

    def fetch_camt(
        self,
        account: SEPAAccount,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[Sequence[bytes], Sequence[bytes]]:
        client = self._client
        with client._get_dialog() as dialog:  # noqa: SLF001 - legacy adapter
            hkcazs, hkcaz = client._find_highest_supported_command(  # noqa: SLF001
                HKCAZ1,
                return_parameter_segment=True,
            )
            camt_messages = client._supported_camt_message_types(hkcazs)
            if not camt_messages:
                camt_messages = (
                    'urn:iso:std:iso:20022:tech:xsd:camt.052.001.02',
                )
            supported_messages = SupportedMessageTypes(list(camt_messages))
            logger.info('Start fetching from %s to %s', start_date, end_date)
            responses = client._fetch_with_touchdowns(  # noqa: SLF001
                dialog,
                lambda touchdown: hkcaz(
                    account=hkcaz._fields['account'].type.from_sepa_account(account),
                    all_accounts=False,
                    date_start=start_date,
                    date_end=end_date,
                    touchdown_point=touchdown,
                    supported_camt_messages=supported_messages,
                ),
                self._response_handler_get_transactions_xml,
                'HICAZ',
            )
            logger.info('Fetching done.')
        return responses

    @staticmethod
    def _mt940_segments(responses: Iterable, include_pending: bool) -> Iterable[str]:
        booked = [seg.statement_booked.decode('iso-8859-1') for seg in responses]
        if include_pending:
            booked.extend(
                seg.statement_pending.decode('iso-8859-1')
                for seg in responses
                if seg.statement_pending
            )
        return booked

    @staticmethod
    def _response_handler_get_transactions_xml(responses) -> tuple[Sequence, Sequence]:
        booked_streams = []
        pending_streams = []
        for seg in responses:
            booked_streams.extend(seg.statement_booked.camt_statements)
            pending_streams.append(seg.statement_pending)
        return booked_streams, pending_streams
