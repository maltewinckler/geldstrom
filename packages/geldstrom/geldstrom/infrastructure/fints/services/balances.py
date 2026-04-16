"""FinTS 3.0 balance service - connection management and domain mapping."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime, time
from typing import TYPE_CHECKING

from geldstrom.domain import Account, BalanceAmount, BalanceSnapshot
from geldstrom.infrastructure.fints.session import FinTSSessionState
from geldstrom.infrastructure.fints.support.helpers import (
    account_key,
    locate_sepa_account,
)

from .base import FinTSServiceBase

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class FinTSBalanceService(FinTSServiceBase):
    """Manages FinTS connections for balance queries; maps results to domain types."""

    def fetch_balances(
        self,
        state: FinTSSessionState,
        account_ids: Sequence[str] | None = None,
    ) -> Sequence[BalanceSnapshot]:
        from geldstrom.infrastructure.fints.operations import (
            AccountOperations,
            BalanceOperations,
        )

        helper = self._make_helper()
        results: list[BalanceSnapshot] = []

        with helper.connect(state) as ctx:
            account_ops = AccountOperations(ctx.dialog, ctx.parameters)
            balance_ops = BalanceOperations(ctx.dialog, ctx.parameters)
            sepa_accounts = account_ops.fetch_sepa_accounts()
            sepa_lookup = {account_key(sepa): sepa for sepa in sepa_accounts}
            target_ids = account_ids or list(sepa_lookup.keys())
            if account_ids is not None:
                unknown_ids = set(account_ids) - set(sepa_lookup.keys())
                if unknown_ids:
                    raise ValueError(
                        f"Unknown account ID(s): {', '.join(sorted(unknown_ids))}"
                    )

            for account_id in target_ids:
                sepa = sepa_lookup.get(account_id)
                if not sepa:
                    continue

                try:
                    result = balance_ops.fetch_balance(sepa)
                    snapshot = self._balance_from_operations(account_id, result)
                    results.append(snapshot)
                except Exception as e:
                    logger.warning("Failed to fetch balance for %s: %s", account_id, e)
                    continue

        return tuple(results)

    def fetch_balance(
        self,
        state: FinTSSessionState,
        account: Account,
    ) -> BalanceSnapshot:
        from geldstrom.infrastructure.fints.operations import (
            AccountOperations,
            BalanceOperations,
        )

        helper = self._make_helper()

        with helper.connect(state) as ctx:
            account_ops = AccountOperations(ctx.dialog, ctx.parameters)
            balance_ops = BalanceOperations(ctx.dialog, ctx.parameters)

            sepa_account = locate_sepa_account(account_ops, account.account_id)
            result = balance_ops.fetch_balance(sepa_account)
            return self._balance_from_operations(account.account_id, result)

    def _balance_from_operations(
        self,
        account_id: str,
        result,
    ) -> BalanceSnapshot:
        from geldstrom.infrastructure.fints.operations import BalanceResult

        if not isinstance(result, BalanceResult):
            raise ValueError(f"Unexpected result type: {type(result)}")

        booked = result.booked
        booked_amount = self._hisal_balance_to_amount(booked)
        as_of = datetime.combine(booked.date, time.min)
        pending_amount = None
        if result.pending:
            pending_amount = self._hisal_balance_to_amount(result.pending)
        available_amount = None
        if result.available is not None:
            available_amount = BalanceAmount(
                amount=result.available,
                currency=booked.currency,
            )

        credit_limit_amount = None
        if result.credit_line is not None:
            credit_limit_amount = BalanceAmount(
                amount=result.credit_line,
                currency=booked.currency,
            )

        return BalanceSnapshot(
            account_id=account_id,
            as_of=as_of,
            booked=booked_amount,
            pending=pending_amount,
            available=available_amount,
            credit_limit=credit_limit_amount,
        )

    def _hisal_balance_to_amount(self, hisal_balance) -> BalanceAmount:
        """Convert HisalBalance to BalanceAmount with correct sign."""
        amount = (
            hisal_balance.amount if hisal_balance.is_credit else -hisal_balance.amount
        )
        return BalanceAmount(amount=amount, currency=hisal_balance.currency)


__all__ = ["FinTSBalanceService"]
