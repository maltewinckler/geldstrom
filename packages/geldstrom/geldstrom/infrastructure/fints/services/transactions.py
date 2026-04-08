"""FinTS 3.0 transaction history adapter — thin orchestrator.

Delegates MT940/CAMT parsing to the dedicated pipeline modules in
``operations.transactions.mt940`` and ``operations.transactions.camt``.
"""

from __future__ import annotations

import logging
from datetime import date

from geldstrom.domain import TransactionFeed
from geldstrom.infrastructure.fints.exceptions import FinTSUnsupportedOperation
from geldstrom.infrastructure.fints.session import FinTSSessionState
from geldstrom.infrastructure.fints.support.helpers import locate_sepa_account

from .base import FinTSServiceBase

logger = logging.getLogger(__name__)


class FinTSTransactionService(FinTSServiceBase):
    """Manages FinTS connections for transaction history; maps results to domain types."""

    def fetch_history(
        self,
        state: FinTSSessionState,
        account_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        *,
        include_pending: bool = False,
    ) -> TransactionFeed:
        from geldstrom.infrastructure.fints.operations import AccountOperations
        from geldstrom.infrastructure.fints.operations.transactions import (
            CamtFetcher,
            Mt940Fetcher,
        )

        helper = self._make_helper()

        with helper.connect(state) as ctx:
            account_ops = AccountOperations(ctx.dialog, ctx.parameters)
            sepa_account = locate_sepa_account(account_ops, account_id)

            mt940 = Mt940Fetcher(ctx.dialog, ctx.parameters)
            camt = CamtFetcher(ctx.dialog, ctx.parameters)

            if include_pending:
                return self._fetch_with_camt_preferred(
                    mt940,
                    camt,
                    sepa_account,
                    account_id,
                    start_date,
                    end_date,
                    include_pending,
                )
            return self._fetch_with_mt940_preferred(
                mt940,
                camt,
                sepa_account,
                account_id,
                start_date,
                end_date,
            )

    @staticmethod
    def _fetch_with_mt940_preferred(
        mt940: object,
        camt: object,
        sepa_account: object,
        account_id: str,
        start_date: date | None,
        end_date: date | None,
    ) -> TransactionFeed:
        """Fetch transactions preferring MT940, falling back to CAMT."""
        try:
            return mt940.fetch(sepa_account, account_id, start_date, end_date)
        except FinTSUnsupportedOperation:
            return camt.fetch(sepa_account, account_id, start_date, end_date)

    @staticmethod
    def _fetch_with_camt_preferred(
        mt940: object,
        camt: object,
        sepa_account: object,
        account_id: str,
        start_date: date | None,
        end_date: date | None,
        include_pending: bool,
    ) -> TransactionFeed:
        """Fetch transactions preferring CAMT, falling back to MT940."""
        try:
            return camt.fetch(
                sepa_account,
                account_id,
                start_date,
                end_date,
                include_pending=include_pending,
            )
        except FinTSUnsupportedOperation:
            logger.warning(
                "Bank does not support CAMT; falling back to MT940 "
                "(pending transactions will not be included)"
            )
            return mt940.fetch(sepa_account, account_id, start_date, end_date)


__all__ = ["FinTSTransactionService"]
