"""Deterministic fake banking connector for application tests."""

from __future__ import annotations

from collections import deque
from datetime import date

from gateway.domain.banking_gateway import (
    AccountsResult,
    BalancesResult,
    FinTSInstitute,
    ResumeResult,
    TanMethodsResult,
    TransactionsResult,
)
from gateway.domain.banking_gateway.value_objects import (
    PresentedBankCredentials,
    RequestedIban,
)


class FakeBankingConnector:
    """Returns queued results for banking operations in a deterministic order."""

    def __init__(
        self,
        *,
        accounts_results: list[AccountsResult] | None = None,
        balances_results: list[BalancesResult] | None = None,
        transactions_results: list[TransactionsResult] | None = None,
        tan_methods_results: list[TanMethodsResult] | None = None,
        resume_results: list[ResumeResult] | None = None,
    ) -> None:
        self._accounts_results = deque(accounts_results or [])
        self._balances_results = deque(balances_results or [])
        self._transactions_results = deque(transactions_results or [])
        self._tan_methods_results = deque(tan_methods_results or [])
        self._resume_results = deque(resume_results or [])
        self.calls: list[tuple[str, object]] = []

    async def list_accounts(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
    ) -> AccountsResult:
        self.calls.append(
            ("list_accounts", {"institute": institute, "credentials": credentials})
        )
        return self._pop_result(self._accounts_results, "list_accounts")

    async def get_balances(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
    ) -> BalancesResult:
        self.calls.append(
            ("get_balances", {"institute": institute, "credentials": credentials})
        )
        return self._pop_result(self._balances_results, "get_balances")

    async def fetch_transactions(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
        iban: RequestedIban,
        start_date: date,
        end_date: date,
    ) -> TransactionsResult:
        self.calls.append(
            (
                "fetch_transactions",
                {
                    "institute": institute,
                    "credentials": credentials,
                    "iban": iban,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            )
        )
        return self._pop_result(self._transactions_results, "fetch_transactions")

    async def get_tan_methods(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
    ) -> TanMethodsResult:
        self.calls.append(
            (
                "get_tan_methods",
                {"institute": institute, "credentials": credentials},
            )
        )
        return self._pop_result(self._tan_methods_results, "get_tan_methods")

    async def resume_operation(self, session_state: bytes) -> ResumeResult:
        self.calls.append(("resume_operation", session_state))
        return self._pop_result(self._resume_results, "resume_operation")

    def queue_balances_result(self, result: BalancesResult) -> None:
        self._balances_results.append(result)

    def queue_accounts_result(self, result: AccountsResult) -> None:
        self._accounts_results.append(result)

    def queue_transactions_result(self, result: TransactionsResult) -> None:
        self._transactions_results.append(result)

    def queue_tan_methods_result(self, result: TanMethodsResult) -> None:
        self._tan_methods_results.append(result)

    def queue_resume_result(self, result: ResumeResult) -> None:
        self._resume_results.append(result)

    @staticmethod
    def _pop_result(queue: deque, operation_name: str):
        if not queue:
            raise AssertionError(f"No queued fake result for {operation_name}")
        return queue.popleft()
