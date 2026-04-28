"""FinTS 3.0 client with non-blocking decoupled TAN handling."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

from pydantic import BaseModel

from geldstrom.domain import (
    Account,
    BalanceSnapshot,
    TransactionFeed,
)
from geldstrom.infrastructure.fints.challenge import (
    Challenge,
    ChallengeHandler,
    DecoupledTANPending,
    DetachingChallengeHandler,
    TANConfig,
)
from geldstrom.infrastructure.fints.operations.transactions import (
    parse_camt_approved_response,
    parse_mt940_approved_response,
)
from geldstrom.infrastructure.fints.session import FinTSSessionState
from geldstrom.infrastructure.fints.support.connection import ConnectionContext
from geldstrom.infrastructure.fints.tan import TANMethod

from .fints3 import FinTS3Client

logger = logging.getLogger(__name__)


class PollResult(BaseModel):
    """Result of a single decoupled TAN poll."""

    status: str  # "pending", "approved", "failed", "expired"
    operation_type: str | None = None  # set when status=="approved"
    data: Any = None
    error: str | None = None


@dataclass
class _PendingTANState:
    context: ConnectionContext
    task_reference: str
    challenge: Challenge | None
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
        session_state: FinTSSessionState | None,
        challenge_handler: ChallengeHandler | None,
        tan_config: TANConfig | None,
    ) -> None:
        super()._init_common(
            session_state,
            challenge_handler or DetachingChallengeHandler(),
            tan_config,
        )
        self._pending: _PendingTANState | None = None

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
                context=pending.context,
                task_reference=pending.task_reference,
                challenge=pending.challenge,
                operation_type="transactions",
                operation_meta={
                    "account_id": account_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "include_pending": include_pending,
                    "was_connected": self._connected,
                },
            )
            self._store_session_state(pending.context)
            raise

    def connect(self) -> Sequence[Account]:
        try:
            return super().connect()
        except DecoupledTANPending as pending:
            self._pending = _PendingTANState(
                context=pending.context,
                task_reference=pending.task_reference,
                challenge=pending.challenge,
                operation_type="connect",
                operation_meta={"was_connected": self._connected},
            )
            self._store_session_state(pending.context)
            raise

    def list_accounts(self) -> Sequence[Account]:
        try:
            return super().list_accounts()
        except DecoupledTANPending as pending:
            self._pending = _PendingTANState(
                context=pending.context,
                task_reference=pending.task_reference,
                challenge=pending.challenge,
                operation_type="accounts",
                operation_meta={"was_connected": self._connected},
            )
            self._store_session_state(pending.context)
            raise

    def get_balance(self, account: Account | str) -> BalanceSnapshot:
        try:
            return super().get_balance(account)
        except DecoupledTANPending as pending:
            account_id = account.account_id if isinstance(account, Account) else account
            self._pending = _PendingTANState(
                context=pending.context,
                task_reference=pending.task_reference,
                challenge=pending.challenge,
                operation_type="balance",
                operation_meta={
                    "account_id": account_id,
                    "was_connected": self._connected,
                },
            )
            self._store_session_state(pending.context)
            raise

    def get_balances(
        self,
        account_ids: Sequence[str] | None = None,
    ) -> Sequence[BalanceSnapshot]:
        try:
            return super().get_balances(account_ids)
        except DecoupledTANPending as pending:
            self._pending = _PendingTANState(
                context=pending.context,
                task_reference=pending.task_reference,
                challenge=pending.challenge,
                operation_type="balances",
                operation_meta={
                    "account_ids": tuple(account_ids)
                    if account_ids is not None
                    else None,
                    "was_connected": self._connected,
                },
            )
            self._store_session_state(pending.context)
            raise

    def get_tan_methods(self) -> Sequence[TANMethod]:
        try:
            return super().get_tan_methods()
        except DecoupledTANPending as pending:
            self._pending = _PendingTANState(
                context=pending.context,
                task_reference=pending.task_reference,
                challenge=pending.challenge,
                operation_type="tan_methods",
                operation_meta={"was_connected": self._connected},
            )
            self._store_session_state(pending.context)
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

        # TAN approved - parse the response based on operation type
        data = self._complete_approved_operation(response)
        self.cleanup_pending()
        return PollResult(status="approved", data=data)

    def _complete_approved_operation(self, response) -> Any:
        op = self._pending
        if op is None:
            return None

        ctx = op.context

        if op.operation_type in {"connect", "accounts"}:
            return self._resume_accounts_from_context(ctx)

        if op.operation_type == "tan_methods":
            return self._extract_tan_methods_from_context(ctx)

        was_connected = bool(op.operation_meta.get("was_connected", self._connected))
        if not was_connected:
            self._resume_accounts_from_context(ctx)

        if op.operation_type == "transactions":
            account_id = op.operation_meta.get("account_id", "")

            # DKB-style banks require TAN even for connect/list_accounts.
            # When that happens the snapshot stores only the IBAN (no account_id yet).
            # self._accounts was just populated by _resume_accounts_from_context above,
            # so we can resolve IBAN → account_id here without another bank round-trip.
            if not account_id:
                iban = op.operation_meta.get("iban", "")
                if iban and self._accounts:
                    matched = next((a for a in self._accounts if a.iban == iban), None)
                    if matched:
                        account_id = matched.account_id

            # Dates may be ISO strings (from JSON snapshot) or date objects (in-process).
            start_date_raw = op.operation_meta.get("start_date")
            end_date_raw = op.operation_meta.get("end_date")
            start_date = (
                date.fromisoformat(start_date_raw)
                if isinstance(start_date_raw, str)
                else start_date_raw
            )
            end_date = (
                date.fromisoformat(end_date_raw)
                if isinstance(end_date_raw, str)
                else end_date_raw
            )

            logger.debug(
                "_complete_approved_operation: transactions "
                "was_connected=%s account_id=%s start=%s end=%s response_type=%s",
                was_connected,
                account_id,
                start_date,
                end_date,
                type(response).__name__,
            )

            if was_connected and account_id:
                feed = parse_mt940_approved_response(response, account_id)
                if feed.entries:
                    logger.debug(
                        "_complete_approved_operation: found %d MT940 entries in TAN response",
                        len(feed.entries),
                    )
                    self._store_session_state(ctx)
                    return feed

                feed = parse_camt_approved_response(response, account_id)
                if feed.entries:
                    logger.debug(
                        "_complete_approved_operation: found %d CAMT entries in TAN response",
                        len(feed.entries),
                    )
                    self._store_session_state(ctx)
                    return feed

                logger.debug(
                    "_complete_approved_operation: no entries in TAN response; falling back to _fetch_transactions_from_context"
                )

            return self._fetch_transactions_from_context(
                ctx,
                account_id,
                start_date,
                end_date,
                include_pending=bool(op.operation_meta.get("include_pending", False)),
            )

        if op.operation_type == "balance":
            return self._fetch_balance_from_context(
                ctx,
                op.operation_meta["account_id"],
            )

        if op.operation_type == "balances":
            return self._fetch_balances_from_context(
                ctx,
                op.operation_meta.get("account_ids"),
            )

        return None

    def _resume_accounts_from_context(
        self,
        ctx: ConnectionContext,
    ) -> Sequence[Account]:
        discovery = self._get_account_service().discover_from_context(ctx)
        self._accounts = discovery.accounts
        self._capabilities = discovery.capabilities
        self._connected = True
        self._store_session_state(ctx)
        return self._accounts

    def _fetch_balance_from_context(
        self,
        ctx: ConnectionContext,
        account_id: str,
    ) -> BalanceSnapshot:
        from geldstrom.infrastructure.fints.operations import (
            AccountOperations,
            BalanceOperations,
        )
        from geldstrom.infrastructure.fints.support.helpers import locate_sepa_account

        account_ops = AccountOperations(ctx.dialog, ctx.parameters)
        balance_ops = BalanceOperations(ctx.dialog, ctx.parameters)
        sepa_account = locate_sepa_account(account_ops, account_id)
        result = balance_ops.fetch_balance(sepa_account)
        snapshot = self._get_balance_service()._balance_from_operations(
            account_id,
            result,
        )
        self._store_session_state(ctx)
        return snapshot

    def _fetch_balances_from_context(
        self,
        ctx: ConnectionContext,
        account_ids: Sequence[str] | None,
    ) -> Sequence[BalanceSnapshot]:
        from geldstrom.infrastructure.fints.operations import (
            AccountOperations,
            BalanceOperations,
        )
        from geldstrom.infrastructure.fints.support.helpers import account_key

        account_ops = AccountOperations(ctx.dialog, ctx.parameters)
        balance_ops = BalanceOperations(ctx.dialog, ctx.parameters)
        balance_service = self._get_balance_service()

        sepa_accounts = account_ops.fetch_sepa_accounts()
        sepa_lookup = {account_key(sepa): sepa for sepa in sepa_accounts}
        target_ids = account_ids or tuple(sepa_lookup.keys())
        if account_ids is not None:
            unknown_ids = set(account_ids) - set(sepa_lookup.keys())
            if unknown_ids:
                raise ValueError(
                    f"Unknown account ID(s): {', '.join(sorted(unknown_ids))}"
                )

        results: list[BalanceSnapshot] = []
        for account_id in target_ids:
            sepa = sepa_lookup.get(account_id)
            if not sepa:
                continue
            try:
                result = balance_ops.fetch_balance(sepa)
                results.append(
                    balance_service._balance_from_operations(account_id, result)
                )
            except Exception as e:
                logger.warning("Failed to fetch balance for %s: %s", account_id, e)

        self._store_session_state(ctx)
        return tuple(results)

    def _fetch_transactions_from_context(
        self,
        ctx: ConnectionContext,
        account_id: str,
        start_date: date | None,
        end_date: date | None,
        *,
        include_pending: bool,
    ) -> TransactionFeed:
        from geldstrom.infrastructure.fints.operations import AccountOperations
        from geldstrom.infrastructure.fints.operations.transactions import (
            CamtFetcher,
            Mt940Fetcher,
        )
        from geldstrom.infrastructure.fints.support.helpers import locate_sepa_account

        account_ops = AccountOperations(ctx.dialog, ctx.parameters)
        sepa_account = locate_sepa_account(account_ops, account_id)
        mt940 = Mt940Fetcher(ctx.dialog, ctx.parameters)
        camt = CamtFetcher(ctx.dialog, ctx.parameters)
        transaction_service = self._get_transaction_service()

        if include_pending:
            feed = transaction_service._fetch_with_camt_preferred(
                mt940,
                camt,
                sepa_account,
                account_id,
                start_date,
                end_date,
                include_pending,
            )
        else:
            feed = transaction_service._fetch_with_mt940_preferred(
                mt940,
                camt,
                sepa_account,
                account_id,
                start_date,
                end_date,
            )

        self._store_session_state(ctx)
        return feed

    def _extract_tan_methods_from_context(
        self,
        ctx: ConnectionContext,
    ) -> Sequence[TANMethod]:
        methods = self._get_tan_methods_service()._extract_tan_methods(ctx.parameters)
        self._store_session_state(ctx)
        return methods

    def _store_session_state(self, ctx: ConnectionContext | None) -> None:
        if ctx is None:
            return
        self._session_state = self._get_session_helper().create_session_state(ctx)

    def snapshot_pending(self) -> bytes:
        """Serialize the pending TAN state and release the live connection.

        Returns the ``DecoupledSessionSnapshot`` as bytes for external storage
        (e.g. Redis). After this call the live dialog and connection are closed -
        resumption must go through ``FinTSConnectionHelper.resume_for_polling()``
        with fresh credentials.

        Raises ``RuntimeError`` if there is no pending TAN challenge.
        """
        from geldstrom.infrastructure.fints.session_snapshot import (
            DecoupledSessionSnapshot,
        )

        if self._pending is None:
            raise RuntimeError("No pending TAN challenge to snapshot")

        ctx = self._pending.context
        helper = self._get_session_helper()

        # Capture the dialog snapshot (dialog_id, message_number, …)
        dialog_snapshot = ctx.dialog.snapshot()

        # Serialize ParameterStore + system_id via FinTSSessionState
        session_state = helper.create_session_state(ctx)
        fints_session_state = session_state.serialize()

        snapshot = DecoupledSessionSnapshot(
            dialog_snapshot=dialog_snapshot.to_dict(),
            task_reference=self._pending.task_reference,
            fints_session_state=fints_session_state,
            server_url=ctx.credentials.server_url,
            operation_type=self._pending.operation_type,
            operation_meta=self._pending.operation_meta,
        )

        serialized = snapshot.serialize()

        # Release only the network connection - do NOT send HKEND, because
        # the dialog must remain open at the bank so that subsequent
        # HKTAN process=S poll messages are accepted.
        pending = self._pending
        self._pending = None
        try:
            if pending.context.connection is not None:
                pending.context.connection.close()
        except Exception:
            logger.debug("Error closing connection after snapshot", exc_info=True)

        return serialized

    @property
    def has_pending_tan(self) -> bool:
        return self._pending is not None

    def resume_and_poll(self, snapshot_bytes: bytes) -> PollResult:
        """Resume a serialized pending TAN session and send one poll message.

        Designed for stateless gateways: the caller serializes the session to
        external storage after each request and passes the bytes back here on
        the next poll request (with fresh credentials on ``self``).

        Returns:
          ``PollResult(status="pending",  data=<updated_snapshot_bytes>)``
          ``PollResult(status="approved", operation_type=<str>, data=<domain_result>)``
          ``PollResult(status="failed",   error=<reason>)``
        """
        from geldstrom.infrastructure.fints.dialog import DialogSnapshot
        from geldstrom.infrastructure.fints.session_snapshot import (
            DecoupledSessionSnapshot,
        )

        try:
            snapshot = DecoupledSessionSnapshot.deserialize(snapshot_bytes)
        except Exception as exc:
            return PollResult(status="failed", error=f"Invalid session snapshot: {exc}")

        helper = self._get_session_helper()
        ctx = helper.resume_for_polling(
            snapshot=DialogSnapshot.from_dict(snapshot.dialog_snapshot),
            fints_session_state=snapshot.fints_session_state,
            server_url=snapshot.server_url,
        )

        try:
            response = ctx.dialog.poll_decoupled_once(snapshot.task_reference)
        except (TimeoutError, ValueError) as exc:
            _close_ctx(ctx)
            return PollResult(status="failed", error=str(exc))

        if response is None:
            # Still pending - persist the updated dialog state for next poll.
            updated = DecoupledSessionSnapshot(
                dialog_snapshot=ctx.dialog.snapshot().to_dict(),
                task_reference=snapshot.task_reference,
                fints_session_state=helper.create_session_state(ctx).serialize(),
                server_url=snapshot.server_url,
                operation_type=snapshot.operation_type,
                operation_meta=snapshot.operation_meta,
            )
            _close_connection_only(ctx)
            return PollResult(status="pending", data=updated.serialize())

        # TAN approved - rehydrate _pending so _complete_approved_operation works.
        self._pending = _PendingTANState(
            context=ctx,
            task_reference=snapshot.task_reference,
            challenge=None,
            operation_type=snapshot.operation_type,
            operation_meta=snapshot.operation_meta,
        )
        try:
            data = self._complete_approved_operation(response)
        finally:
            self._pending = None
            _close_ctx(ctx)

        return PollResult(
            status="approved",
            operation_type=snapshot.operation_type,
            data=data,
        )

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


def _close_ctx(ctx: ConnectionContext) -> None:
    """Best-effort close of a resumed dialog (sends HKEND then closes connection)."""
    try:
        if ctx.dialog.is_open:
            ctx.dialog.end()
    except Exception:
        logger.debug("Error closing resumed dialog", exc_info=True)
    try:
        if ctx.connection is not None:
            ctx.connection.close()
    except Exception:
        logger.debug("Error closing resumed connection", exc_info=True)


def _close_connection_only(ctx: ConnectionContext) -> None:
    """Close only the TCP connection; leave the bank dialog open for next poll."""
    try:
        if ctx.connection is not None:
            ctx.connection.close()
    except Exception:
        logger.debug("Error closing connection", exc_info=True)


__all__ = ["FinTS3ClientDecoupled", "PollResult"]
