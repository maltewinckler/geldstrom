"""High level use-case services for the read-only FinTS client."""
from __future__ import annotations

from datetime import date
from typing import Sequence

from fints.domain import (
    Account,
    BalanceSnapshot,
    BankCapabilities,
    SessionState,
    TransactionFeed,
)

from .ports import BankGateway, GatewayCredentials


class AccountDiscoveryService:
    def __init__(self, gateway: BankGateway):
        self._gateway = gateway

    def execute(
        self,
        credentials: GatewayCredentials,
        session: SessionState | None = None,
    ) -> tuple[SessionState, BankCapabilities, Sequence[Account]]:
        state = self._gateway.open_session(credentials, existing_state=session)
        capabilities = self._gateway.fetch_bank_capabilities(credentials, state)
        accounts = self._gateway.fetch_accounts(credentials, state)
        return state, capabilities, accounts


class BalanceService:
    def __init__(self, gateway: BankGateway):
        self._gateway = gateway

    def fetch(
        self,
        credentials: GatewayCredentials,
        session: SessionState,
        account: Account,
    ) -> BalanceSnapshot:
        return self._gateway.fetch_balance(credentials, session, account)


class TransactionHistoryService:
    def __init__(self, gateway: BankGateway):
        self._gateway = gateway

    def fetch(
        self,
        credentials: GatewayCredentials,
        session: SessionState,
        account: Account,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> TransactionFeed:
        return self._gateway.fetch_transactions(
            credentials,
            session,
            account,
            start_date,
            end_date,
        )
