"""Domain ports for bank-facing gateway operations."""

from __future__ import annotations

from datetime import date, datetime
from typing import Protocol

from gateway.domain.banking_gateway.value_objects import FinTSInstitute

from .operations import (
    AccountsResult,
    BalancesResult,
    PendingOperationSession,
    ResumeResult,
    TanMethodsResult,
    TransactionsResult,
)
from .value_objects import PresentedBankCredentials, RequestedIban


class BankingConnector(Protocol):
    """Abstracts protocol-specific bank connectivity from the application layer."""

    async def list_accounts(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
    ) -> AccountsResult: ...

    async def fetch_transactions(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
        iban: RequestedIban,
        start_date: date,
        end_date: date,
    ) -> TransactionsResult: ...

    async def get_balances(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
    ) -> BalancesResult: ...

    async def get_tan_methods(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
    ) -> TanMethodsResult: ...

    async def resume_operation(
        self,
        session_state: bytes,
        credentials: PresentedBankCredentials,
        institute: FinTSInstitute,
    ) -> ResumeResult: ...


class OperationSessionStore(Protocol):
    """Ephemeral runtime store for pending decoupled operations."""

    async def create(self, session: PendingOperationSession) -> None: ...

    async def get(self, operation_id: str) -> PendingOperationSession | None: ...

    async def update(self, session: PendingOperationSession) -> None: ...

    async def delete(self, operation_id: str) -> None: ...

    async def expire_stale(self, now: datetime) -> int: ...

    async def list_all(self) -> list[PendingOperationSession]: ...
