"""Gateway that provides unified access to FinTS banking operations.

This gateway implements the BankGateway protocol by delegating to
the appropriate infrastructure adapters. It provides a unified interface
for the application layer while the adapters handle protocol details.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Sequence

from geldstrom.application.ports import BankGateway, GatewayCredentials
from geldstrom.domain import (
    Account,
    BalanceSnapshot,
    BankCapabilities,
    TransactionFeed,
)
from geldstrom.infrastructure.fints.adapters import (
    FinTSAccountDiscovery,
    FinTSBalanceAdapter,
    FinTSSessionAdapter,
    FinTSTransactionHistory,
)
from geldstrom.infrastructure.fints.session import FinTSSessionState

logger = logging.getLogger(__name__)


# Type alias for backward compatibility
SessionState = FinTSSessionState


class FinTSReadOnlyGateway(BankGateway):
    """
    Gateway for read-only FinTS banking operations.

    This gateway delegates to the infrastructure adapters, which handle
    the actual FinTS protocol communication using the dialog/operations
    infrastructure.

    Example:
        gateway = FinTSReadOnlyGateway()
        state = gateway.open_session(credentials)
        accounts = gateway.fetch_accounts(credentials, state)
        for account in accounts:
            balance = gateway.fetch_balance(credentials, state, account)
    """

    def __init__(self) -> None:
        """Initialize the gateway."""
        self._session_adapter = FinTSSessionAdapter()

    def open_session(
        self,
        credentials: GatewayCredentials,
        existing_state: FinTSSessionState | None = None,
    ) -> FinTSSessionState:
        """
        Open a banking session.

        Args:
            credentials: Bank connection credentials
            existing_state: Optional existing session to resume

        Returns:
            New or refreshed session state
        """
        return self._session_adapter.open_session(credentials, existing_state)

    def fetch_bank_capabilities(
        self,
        credentials: GatewayCredentials,
        session: FinTSSessionState,
    ) -> BankCapabilities:
        """
        Fetch the bank's supported operations.

        Args:
            credentials: Bank connection credentials
            session: Current session state

        Returns:
            BankCapabilities describing supported operations
        """
        adapter = FinTSAccountDiscovery(credentials)
        return adapter.fetch_bank_capabilities(session)

    def fetch_accounts(
        self,
        credentials: GatewayCredentials,
        session: FinTSSessionState,
    ) -> Sequence[Account]:
        """
        Fetch available accounts.

        Args:
            credentials: Bank connection credentials
            session: Current session state

        Returns:
            Sequence of Account objects
        """
        adapter = FinTSAccountDiscovery(credentials)
        return adapter.fetch_accounts(session)

    def fetch_balance(
        self,
        credentials: GatewayCredentials,
        session: FinTSSessionState,
        account: Account,
    ) -> BalanceSnapshot:
        """
        Fetch balance for an account.

        Args:
            credentials: Bank connection credentials
            session: Current session state
            account: Account to fetch balance for

        Returns:
            BalanceSnapshot with current balance
        """
        adapter = FinTSBalanceAdapter(credentials)
        return adapter.fetch_balance(session, account)

    def fetch_transactions(
        self,
        credentials: GatewayCredentials,
        session: FinTSSessionState,
        account: Account,
        start_date: date | None,
        end_date: date | None,
    ) -> TransactionFeed:
        """
        Fetch transaction history for an account.

        Args:
            credentials: Bank connection credentials
            session: Current session state
            account: Account to fetch transactions for
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            TransactionFeed with transaction entries
        """
        adapter = FinTSTransactionHistory(credentials)
        return adapter.fetch_history(
            session,
            account.account_id,
            start_date,
            end_date,
        )


__all__ = ["FinTSReadOnlyGateway", "SessionState"]
