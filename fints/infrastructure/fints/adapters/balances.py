"""FinTS 3.0 implementation of BalancePort."""
from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Sequence

from fints.application.ports import GatewayCredentials
from fints.domain import Account, BalanceAmount, BalanceSnapshot
from fints.domain.ports.balances import BalancePort
from fints.infrastructure.fints.session import FinTSSessionState

from .connection import FinTSConnectionHelper

if TYPE_CHECKING:
    from fints.client import FinTS3PinTanClient
    from fints.models import SEPAAccount

logger = logging.getLogger(__name__)


# Feature flag to enable new infrastructure
# The new infrastructure uses dialog/operations modules directly
USE_NEW_INFRASTRUCTURE = True


class FinTSBalanceAdapter(BalancePort):
    """
    FinTS 3.0 implementation of BalancePort.

    Fetches account balances via HKSAL segments.
    """

    def __init__(
        self,
        credentials: GatewayCredentials,
        accounts: Sequence[Account] | None = None,
    ) -> None:
        """
        Initialize with credentials and optional account list.

        Args:
            credentials: Bank connection credentials
            accounts: Optional pre-fetched account list for account lookup
        """
        self._credentials = credentials
        self._accounts = {acc.account_id: acc for acc in (accounts or [])}

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
        if USE_NEW_INFRASTRUCTURE:
            return self._fetch_balances_new(state, account_ids)
        return self._fetch_balances_legacy(state, account_ids)

    def _fetch_balances_new(
        self,
        state: FinTSSessionState,
        account_ids: Sequence[str] | None,
    ) -> Sequence[BalanceSnapshot]:
        """Fetch balances using new infrastructure."""
        from fints.infrastructure.fints.operations import (
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
            sepa_lookup = {self._account_key(sepa): sepa for sepa in sepa_accounts}

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

    def _fetch_balances_legacy(
        self,
        state: FinTSSessionState,
        account_ids: Sequence[str] | None,
    ) -> Sequence[BalanceSnapshot]:
        """Fetch balances using legacy client."""
        client = self._build_client(state)
        results: list[BalanceSnapshot] = []

        with self._logged_in(client):
            sepa_accounts = client.get_sepa_accounts()
            sepa_lookup = {self._account_key(sepa): sepa for sepa in sepa_accounts}

            # Determine which accounts to fetch
            target_ids = account_ids or list(sepa_lookup.keys())

            for account_id in target_ids:
                sepa = sepa_lookup.get(account_id)
                if not sepa:
                    continue

                try:
                    booked = client.get_balance(sepa)
                    snapshot = self._balance_from_mt940(account_id, booked)
                    results.append(snapshot)
                except Exception:
                    # Skip accounts that fail balance retrieval
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
        if USE_NEW_INFRASTRUCTURE:
            return self._fetch_balance_new(state, account)
        return self._fetch_balance_legacy(state, account)

    def _fetch_balance_new(
        self,
        state: FinTSSessionState,
        account: Account,
    ) -> BalanceSnapshot:
        """Fetch single balance using new infrastructure."""
        from fints.infrastructure.fints.operations import (
            AccountOperations,
            BalanceOperations,
        )

        helper = FinTSConnectionHelper(self._credentials)

        with helper.connect(state) as ctx:
            account_ops = AccountOperations(ctx.dialog, ctx.parameters)
            balance_ops = BalanceOperations(ctx.dialog, ctx.parameters)

            sepa_account = self._locate_sepa_account_new(account_ops, account)
            result = balance_ops.fetch_balance(sepa_account)
            return self._balance_from_operations(account.account_id, result)

    def _fetch_balance_legacy(
        self,
        state: FinTSSessionState,
        account: Account,
    ) -> BalanceSnapshot:
        """Fetch single balance using legacy client."""
        client = self._build_client(state)

        with self._logged_in(client):
            sepa_account = self._locate_sepa_account(client, account)
            booked = client.get_balance(sepa_account)

        return self._balance_from_mt940(account.account_id, booked)

    # --- New infrastructure helpers ---

    def _balance_from_operations(
        self,
        account_id: str,
        result,
    ) -> BalanceSnapshot:
        """Convert operations BalanceResult to domain BalanceSnapshot."""
        from fints.infrastructure.fints.operations import BalanceResult

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

    def _locate_sepa_account_new(self, account_ops, account: Account) -> "SEPAAccount":
        """Find SEPA account using operations."""
        for sepa in account_ops.fetch_sepa_accounts():
            if self._account_key(sepa) == account.account_id:
                return sepa
        raise ValueError(f"Account {account.account_id} not available from bank")

    # --- Legacy helpers ---

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
    def _balance_from_mt940(account_id: str, booked) -> BalanceSnapshot:
        """Convert MT940 balance to domain BalanceSnapshot."""
        amount = Decimal(str(booked.amount.amount))
        booked_amount = BalanceAmount(amount=amount, currency=booked.amount.currency)
        as_of = datetime.combine(booked.date, time.min)
        return BalanceSnapshot(account_id=account_id, as_of=as_of, booked=booked_amount)

    @staticmethod
    def _account_key(account: "SEPAAccount") -> str:
        """Create lookup key from SEPA account."""
        return f"{account.accountnumber}:{account.subaccount or '0'}"

    def _locate_sepa_account(
        self,
        client: "FinTS3PinTanClient",
        account: Account,
    ) -> "SEPAAccount":
        """Find SEPA account matching domain Account."""
        for sepa in client.get_sepa_accounts():
            if self._account_key(sepa) == account.account_id:
                return sepa
        raise ValueError(f"Account {account.account_id} not available from bank")


__all__ = ["FinTSBalanceAdapter"]
