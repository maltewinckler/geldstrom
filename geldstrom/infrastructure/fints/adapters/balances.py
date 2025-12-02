"""FinTS 3.0 implementation of BalancePort."""
from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime, time
from typing import TYPE_CHECKING

from geldstrom.infrastructure.fints.credentials import GatewayCredentials
from geldstrom.domain import Account, BalanceAmount, BalanceSnapshot
from geldstrom.domain.ports.balances import BalancePort
from geldstrom.infrastructure.fints.session import FinTSSessionState

from .connection import FinTSConnectionHelper
from .helpers import account_key, locate_sepa_account

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class FinTSBalanceAdapter(BalancePort):
    """
    FinTS 3.0 implementation of BalancePort.

    Fetches account balances via HKSAL segments.
    """

    def __init__(self, credentials: GatewayCredentials) -> None:
        """
        Initialize with credentials.

        Args:
            credentials: Bank connection credentials
        """
        self._credentials = credentials

    def fetch_balances(
        self,
        state: FinTSSessionState,
        account_ids: Sequence[str] | None = None,
    ) -> Sequence[BalanceSnapshot]:
        """
        Fetch balances for specified accounts.

        Args:
            state: Current session state
            account_ids: Optional list of account IDs to fetch (default: all)

        Returns:
            Sequence of BalanceSnapshot for each account
        """
        from geldstrom.infrastructure.fints.operations import (
            AccountOperations,
            BalanceOperations,
        )

        helper = FinTSConnectionHelper(self._credentials)
        results: list[BalanceSnapshot] = []

        with helper.connect(state) as ctx:
            account_ops = AccountOperations(ctx.dialog, ctx.parameters)
            balance_ops = BalanceOperations(ctx.dialog, ctx.parameters)

            # Get SEPA accounts
            sepa_accounts = account_ops.fetch_sepa_accounts()
            sepa_lookup = {account_key(sepa): sepa for sepa in sepa_accounts}

            # Determine which accounts to fetch
            target_ids = account_ids or list(sepa_lookup.keys())

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
        """
        Fetch balance for a single account.

        Args:
            state: Current session state
            account: Account to fetch balance for

        Returns:
            BalanceSnapshot for the account

        Raises:
            ValueError: If account not found
        """
        from geldstrom.infrastructure.fints.operations import (
            AccountOperations,
            BalanceOperations,
        )

        helper = FinTSConnectionHelper(self._credentials)

        with helper.connect(state) as ctx:
            account_ops = AccountOperations(ctx.dialog, ctx.parameters)
            balance_ops = BalanceOperations(ctx.dialog, ctx.parameters)

            sepa_account = locate_sepa_account(account_ops, account.account_id)
            result = balance_ops.fetch_balance(sepa_account)
            return self._balance_from_operations(account.account_id, result)

    # --- Helpers ---

    def _balance_from_operations(
        self,
        account_id: str,
        result,
    ) -> BalanceSnapshot:
        """Convert operations BalanceResult to domain BalanceSnapshot."""
        from geldstrom.infrastructure.fints.operations import BalanceResult

        if not isinstance(result, BalanceResult):
            raise ValueError(f"Unexpected result type: {type(result)}")

        booked = result.booked
        amount = booked.amount if booked.is_credit else -booked.amount
        booked_amount = BalanceAmount(amount=amount, currency=booked.currency)
        as_of = datetime.combine(booked.date, time.min)

        return BalanceSnapshot(
            account_id=account_id,
            as_of=as_of,
            booked=booked_amount,
        )

__all__ = ["FinTSBalanceAdapter"]
