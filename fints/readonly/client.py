"""High level convenience client for the read-only architecture."""
from __future__ import annotations

from datetime import date
from typing import Sequence

from fints.application import (
    AccountDiscoveryService,
    BalanceService,
    BankGateway,
    GatewayCredentials,
    TransactionHistoryService,
)
from fints.domain import Account, BalanceSnapshot, SessionState, TransactionFeed
from fints.infrastructure import FinTSReadOnlyGateway


class ReadOnlyFinTSClient:
    """User facing API exposing the new read-only services."""

    def __init__(
        self,
        credentials: GatewayCredentials,
        session_state: SessionState | None = None,
        gateway: BankGateway | None = None,
    ) -> None:
        self._credentials = credentials
        self._session_state = session_state
        self._gateway = gateway or FinTSReadOnlyGateway()
        self._discovery = AccountDiscoveryService(self._gateway)
        self._balances = BalanceService(self._gateway)
        self._transactions = TransactionHistoryService(self._gateway)
        self._accounts: Sequence[Account] = ()
        self._capabilities = None

    def __enter__(self) -> "ReadOnlyFinTSClient":
        self.connect()
        return self

    def __exit__(
        self,
        exc_type,
        exc,
        tb,
    ) -> None:  # pragma: no cover - no cleanup required yet
        return None

    # ---------------------------------------------------------------------

    def connect(self, session_state: SessionState | None = None) -> Sequence[Account]:
        """Synchronise metadata and account capabilities."""

        state_hint = session_state or self._session_state
        state, capabilities, accounts = self._discovery.execute(
            self._credentials,
            session=state_hint,
        )
        self._session_state = state
        self._capabilities = capabilities
        self._accounts = tuple(accounts)
        return self._accounts

    def list_accounts(self) -> Sequence[Account]:
        if not self._accounts:
            return self.connect()
        return self._accounts

    def get_balance(self, account_id: str) -> BalanceSnapshot:
        account = self._require_account(account_id)
        state = self._require_session()
        return self._balances.fetch(self._credentials, state, account)

    def get_transactions(
        self,
        account_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> TransactionFeed:
        account = self._require_account(account_id)
        state = self._require_session()
        return self._transactions.fetch(
            self._credentials,
            state,
            account,
            start_date,
            end_date,
        )

    # ------------------------------------------------------------------

    @property
    def session_state(self) -> SessionState | None:
        return self._session_state

    @property
    def capabilities(self):
        return self._capabilities

    # ------------------------------------------------------------------

    def _require_session(self) -> SessionState:
        if not self._session_state:
            raise RuntimeError("Client not connected. Call connect() first.")
        return self._session_state

    def _require_account(self, account_id: str) -> Account:
        for account in self.list_accounts():
            if account.account_id == account_id:
                return account
        raise ValueError(f"Account {account_id} not known. Call connect() to refresh.")
