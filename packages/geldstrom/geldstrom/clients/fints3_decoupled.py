"""FinTS 3.0 client with non-blocking decoupled TAN handling."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

from geldstrom.domain import (
    Account,
    BalanceSnapshot,
    SessionToken,
    TANConfig,
    TransactionFeed,
)
from geldstrom.domain.connection import (
    Challenge,
    ChallengeHandler,
    DetachingChallengeHandler,
)
from geldstrom.domain.connection.challenge import DecoupledTANPending
from geldstrom.domain.model.tan import TANMethod
from geldstrom.infrastructure.fints.adapters.connection import ConnectionContext
from geldstrom.infrastructure.fints.operations.transactions import (
    TransactionOperations,
)

from .fints3 import FinTS3Client

logger = logging.getLogger(__name__)


@dataclass
class PollResult:
    """Result of a single decoupled TAN poll."""

    status: str  # "pending", "approved", "failed", "expired"
    data: Any = None
    error: str | None = None


@dataclass
class _PendingTANState:
    context: ConnectionContext
    task_reference: str
    challenge: Challenge
    operation_type: str
    operation_meta: dict


class FinTS3ClientDecoupled(FinTS3Client):
    """FinTS 3.0 client that raises immediately on decoupled TAN instead of blocking.

    Usage::

        client = FinTS3ClientDecoupled(...)
        try:
            feed = client.get_transactions(account, start_date=start, end_date=end)
        except DecoupledTANPending:
            # TAN challenge sent to user's banking app
            while True:
                result = client.poll_tan()
                if result.status == "approved":
                    feed = result.data
                    break
                elif result.status == "pending":
                    time.sleep(2)
                else:
                    raise RuntimeError(result.error)
    """

    def _init_common(
        self,
        session_state: SessionToken | None,
        challenge_handler: ChallengeHandler | None,
        tan_config: TANConfig | None,
    ) -> None:
        super()._init_common(
            session_state,
            challenge_handler or DetachingChallengeHandler(),
            tan_config,
        )
        self._pending: _PendingTANState | None = None

    @classmethod
    def from_gateway_credentials(
        cls,
        credentials,
        *,
        session_state: SessionToken | None = None,
        challenge_handler: ChallengeHandler | None = None,
        tan_config: TANConfig | None = None,
    ) -> FinTS3ClientDecoupled:
        instance = cls.__new__(cls)
        instance._credentials = credentials
        instance._init_common(session_state, challenge_handler, tan_config)
        return instance

    def get_transactions(
        self,
        account: Account | str,
        start_date: date | None = None,
        end_date: date | None = None,
        *,
        include_pending: bool = False,
    ) -> TransactionFeed:
        try:
            return super().get_transactions(
                account, start_date, end_date, include_pending=include_pending
            )
        except DecoupledTANPending as pending:
            account_id = account.account_id if isinstance(account, Account) else account
            self._pending = _PendingTANState(
                context=pending.context,  # type: ignore[attr-defined]
                task_reference=pending.task_reference,
                challenge=pending.challenge,
                operation_type="transactions",
                operation_meta={
                    "account_id": account_id,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            )
            raise

    def list_accounts(self) -> Sequence[Account]:
        try:
            return super().list_accounts()
        except DecoupledTANPending as pending:
            self._pending = _PendingTANState(
                context=pending.context,  # type: ignore[attr-defined]
                task_reference=pending.task_reference,
                challenge=pending.challenge,
                operation_type="accounts",
                operation_meta={},
            )
            raise

    def get_balances(
        self,
        account_ids: Sequence[str] | None = None,
    ) -> Sequence[BalanceSnapshot]:
        try:
            return super().get_balances(account_ids)
        except DecoupledTANPending as pending:
            self._pending = _PendingTANState(
                context=pending.context,  # type: ignore[attr-defined]
                task_reference=pending.task_reference,
                challenge=pending.challenge,
                operation_type="balances",
                operation_meta={},
            )
            raise

    def get_tan_methods(self) -> Sequence[TANMethod]:
        try:
            return super().get_tan_methods()
        except DecoupledTANPending as pending:
            self._pending = _PendingTANState(
                context=pending.context,  # type: ignore[attr-defined]
                task_reference=pending.task_reference,
                challenge=pending.challenge,
                operation_type="tan_methods",
                operation_meta={},
            )
            raise

    def poll_tan(self) -> PollResult:
        """Send a single TAN status poll. Returns result immediately."""
        if self._pending is None:
            raise RuntimeError("No pending TAN challenge to poll")

        ctx = self._pending.context
        try:
            response = ctx.dialog.poll_decoupled_once(self._pending.task_reference)
        except (TimeoutError, ValueError) as e:
            self.cleanup_pending()
            return PollResult(status="failed", error=str(e))

        if response is None:
            return PollResult(status="pending")

        # TAN approved — parse the response based on operation type
        data = self._parse_approved_response(response)
        self.cleanup_pending()
        return PollResult(status="approved", data=data)

    def _parse_approved_response(self, response) -> Any:
        op = self._pending
        if op is None:
            return None

        if op.operation_type == "transactions":
            result = TransactionOperations.parse_mt940_from_response(response)
            if result.transactions:
                adapter = self._get_transaction_adapter()
                return adapter._transactions_from_mt940(
                    op.operation_meta["account_id"],
                    result.transactions,
                    has_more=result.has_more,
                )
            # Try CAMT
            camt_result = TransactionOperations.parse_camt_from_response(response)
            if camt_result.booked_documents:
                adapter = self._get_transaction_adapter()
                return adapter._transactions_from_camt(
                    op.operation_meta["account_id"],
                    camt_result.booked_documents,
                    camt_result.pending_documents,
                    has_more=camt_result.has_more,
                )
            return TransactionFeed(
                account_id=op.operation_meta["account_id"],
                entries=[],
                start_date=op.operation_meta.get("start_date") or date.today(),
                end_date=op.operation_meta.get("end_date") or date.today(),
            )

        # For other operation types, return the raw response —
        # the gateway connector will handle the specifics.
        return response

    @property
    def has_pending_tan(self) -> bool:
        return self._pending is not None

    @property
    def pending_challenge(self) -> Challenge | None:
        return self._pending.challenge if self._pending else None

    def cleanup_pending(self) -> None:
        """Close the detached dialog and connection, clearing pending state."""
        if self._pending is None:
            return
        ctx = self._pending.context
        self._pending = None
        try:
            if ctx.dialog.is_open:
                ctx.dialog.end()
        except Exception:
            logger.debug("Error closing detached dialog", exc_info=True)
        try:
            if ctx.connection is not None:
                ctx.connection.close()
        except Exception:
            logger.debug("Error closing detached connection", exc_info=True)

    def disconnect(self) -> None:
        self.cleanup_pending()
        super().disconnect()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cleanup_pending()
        super().__exit__(exc_type, exc_val, exc_tb)


__all__ = ["FinTS3ClientDecoupled", "PollResult"]
