"""Explicit banking connector dispatch by external protocol."""

from __future__ import annotations

from datetime import date

from gateway.domain.banking_gateway import (
    AccountsResult,
    BalancesResult,
    BankingConnector,
    BankProtocol,
    FinTSInstitute,
    ResumeResult,
    TanMethodsResult,
    TransactionsResult,
)
from gateway.domain.banking_gateway.value_objects import (
    PresentedBankCredentials,
    RequestedIban,
)


class BankingConnectorDispatcher(BankingConnector):
    """Routes banking operations to the correct protocol-specific connector."""

    def __init__(self, *, fints_connector: BankingConnector) -> None:
        self._connectors: dict[BankProtocol, BankingConnector] = {
            BankProtocol.FINTS: fints_connector,
        }

    async def list_accounts(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
    ) -> AccountsResult:
        return await self._connectors[BankProtocol.FINTS].list_accounts(
            institute, credentials
        )

    async def fetch_transactions(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
        iban: RequestedIban,
        start_date: date,
        end_date: date,
    ) -> TransactionsResult:
        return await self._connectors[BankProtocol.FINTS].fetch_transactions(
            institute, credentials, iban, start_date, end_date
        )

    async def get_balances(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
    ) -> BalancesResult:
        return await self._connectors[BankProtocol.FINTS].get_balances(
            institute, credentials
        )

    async def get_tan_methods(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
    ) -> TanMethodsResult:
        return await self._connectors[BankProtocol.FINTS].get_tan_methods(
            institute, credentials
        )

    async def resume_operation(self, session_state: bytes) -> ResumeResult:
        return await self._connectors[BankProtocol.FINTS].resume_operation(
            session_state
        )
