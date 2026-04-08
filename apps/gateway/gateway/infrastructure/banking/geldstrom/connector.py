"""Geldstrom-backed implementation of the gateway banking connector."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from pydantic import SecretStr

from gateway.application.common import BankUpstreamUnavailableError, InternalError
from gateway.domain.banking_gateway import (
    AccountsResult,
    BalancesResult,
    BankingConnector,
    FinTSInstitute,
    OperationStatus,
    OperationType,
    ResumeResult,
    TanMethod,
    TanMethodsResult,
    TransactionsResult,
)
from gateway.domain.banking_gateway.value_objects import (
    PresentedBankCredentials,
    RequestedIban,
)
from geldstrom.clients.fints3_decoupled import FinTS3ClientDecoupled
from geldstrom.domain import (
    Account,
    AccountCapabilities,
    AccountOwner,
    BalanceSnapshot,
    BankCredentials,
    BankRoute,
    TransactionEntry,
    TransactionFeed,
)
from geldstrom.infrastructure.fints.challenge import DecoupledTANPending
from geldstrom.infrastructure.fints.credentials import GatewayCredentials
from geldstrom.infrastructure.fints.dialog import DialogSnapshot
from geldstrom.infrastructure.fints.exceptions import (
    FinTSClientPINError,
    FinTSClientTemporaryAuthError,
    FinTSConnectionError,
    FinTSDialogError,
    FinTSNoResponseError,
    FinTSSCARequiredError,
    FinTSUnsupportedOperation,
)
from geldstrom.infrastructure.fints.session_snapshot import DecoupledSessionSnapshot
from geldstrom.infrastructure.fints.support.connection import FinTSConnectionHelper
from geldstrom.infrastructure.fints.tan import TANMethod as GeldstromTanMethod

from .models import GeldstromClient, GeldstromClientFactory

_logger = logging.getLogger(__name__)


class _DefaultGeldstromClientFactory(GeldstromClientFactory):
    def create(
        self,
        credentials: GatewayCredentials,
        session_state=None,
    ) -> GeldstromClient:
        return FinTS3ClientDecoupled.from_gateway_credentials(
            credentials,
            session_state=session_state,
        )


class GeldstromBankingConnector(BankingConnector):
    """Translate gateway banking operations to Geldstrom calls."""

    def __init__(
        self,
        product_key: str,
        *,
        product_version: str,
        client_factory: GeldstromClientFactory | None = None,
    ) -> None:
        self._product_key = product_key
        self._product_version = product_version
        self._client_factory = client_factory or _DefaultGeldstromClientFactory()

    async def list_accounts(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
    ) -> AccountsResult:
        product_key = self._product_key
        return await asyncio.to_thread(
            self._list_accounts_sync,
            institute,
            credentials,
            product_key,
        )

    async def fetch_transactions(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
        iban: RequestedIban,
        start_date: date,
        end_date: date,
    ) -> TransactionsResult:
        product_key = self._product_key
        return await asyncio.to_thread(
            self._fetch_transactions_sync,
            institute,
            credentials,
            iban,
            start_date,
            end_date,
            product_key,
        )

    async def get_balances(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
    ) -> BalancesResult:
        product_key = self._product_key
        return await asyncio.to_thread(
            self._get_balances_sync,
            institute,
            credentials,
            product_key,
        )

    async def get_tan_methods(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
    ) -> TanMethodsResult:
        product_key = self._product_key
        return await asyncio.to_thread(
            self._get_tan_methods_sync,
            institute,
            credentials,
            product_key,
        )

    async def resume_operation(
        self,
        session_state: bytes,
        credentials: PresentedBankCredentials,
        institute: FinTSInstitute,
    ) -> ResumeResult:
        product_key = self._product_key
        return await asyncio.to_thread(
            self._resume_operation_sync,
            session_state,
            credentials,
            institute,
            product_key,
        )

    def _list_accounts_sync(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
        product_key: str,
    ) -> AccountsResult:
        client = self._build_client(institute, credentials, product_key)
        try:
            accounts = client.list_accounts()
        except DecoupledTANPending:
            return self._snapshot_pending(client, AccountsResult)
        return AccountsResult(
            status=OperationStatus.COMPLETED,
            accounts=[_serialize_account(account) for account in accounts],
        )

    def _fetch_transactions_sync(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
        iban: RequestedIban,
        start_date: date,
        end_date: date,
        product_key: str,
    ) -> TransactionsResult:
        client = self._build_client(institute, credentials, product_key)
        try:
            account = self._find_account_by_iban(client.list_accounts(), iban)
            if account is None:
                return TransactionsResult(
                    status=OperationStatus.FAILED,
                    failure_reason=f"No account found for IBAN {iban.value}",
                )
            feed = client.get_transactions(
                account, start_date=start_date, end_date=end_date
            )
        except DecoupledTANPending:
            return self._snapshot_pending(client, TransactionsResult)
        return TransactionsResult(
            status=OperationStatus.COMPLETED,
            transactions=_serialize_transactions(feed),
        )

    def _get_balances_sync(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
        product_key: str,
    ) -> BalancesResult:
        client = self._build_client(institute, credentials, product_key)
        try:
            balances = client.get_balances()
        except DecoupledTANPending:
            return self._snapshot_pending(client, BalancesResult)
        return BalancesResult(
            status=OperationStatus.COMPLETED,
            balances=[_serialize_balance(b) for b in balances],
        )

    def _get_tan_methods_sync(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
        product_key: str,
    ) -> TanMethodsResult:
        client = self._build_client(institute, credentials, product_key)
        try:
            methods = client.get_tan_methods()
        except DecoupledTANPending:
            return self._snapshot_pending(client, TanMethodsResult)
        return TanMethodsResult(
            status=OperationStatus.COMPLETED,
            methods=[_serialize_tan_method(method) for method in methods],
        )

    # ------------------------------------------------------------------
    # Snapshot helpers
    # ------------------------------------------------------------------

    def _snapshot_pending(self, client: FinTS3ClientDecoupled, result_cls: type):
        """Serialize the pending TAN state and return a PENDING result."""
        session_state = client.snapshot_pending()
        expires_at = datetime.now(UTC) + timedelta(minutes=5)
        return result_cls(
            status=OperationStatus.PENDING_CONFIRMATION,
            session_state=session_state,
            expires_at=expires_at,
        )

    # ------------------------------------------------------------------
    # Resume
    # ------------------------------------------------------------------

    def _resume_operation_sync(
        self,
        session_state: bytes,
        credentials: PresentedBankCredentials,
        institute: FinTSInstitute,
        product_key: str,
    ) -> ResumeResult:
        try:
            snapshot = DecoupledSessionSnapshot.deserialize(session_state)
        except Exception as exc:
            raise InternalError(
                "Unable to deserialize pending banking session state"
            ) from exc

        dialog_snapshot = DialogSnapshot.from_dict(snapshot.dialog_snapshot)
        gateway_creds = self._build_gateway_credentials(
            institute, credentials, product_key
        )
        helper = FinTSConnectionHelper(gateway_creds)
        ctx = helper.resume_for_polling(
            snapshot=dialog_snapshot,
            fints_session_state=snapshot.fints_session_state,
            server_url=snapshot.server_url,
        )

        try:
            response = ctx.dialog.poll_decoupled_once(snapshot.task_reference)
        except (TimeoutError, ValueError) as exc:
            self._close_context(ctx)
            return ResumeResult(
                status=OperationStatus.FAILED,
                failure_reason=str(exc),
            )

        if response is None:
            # Still pending — capture updated message_number for next poll
            updated_dialog_snapshot = ctx.dialog.snapshot()
            updated_session_state_obj = helper.create_session_state(ctx)
            updated_snapshot = DecoupledSessionSnapshot(
                dialog_snapshot=updated_dialog_snapshot.to_dict(),
                task_reference=snapshot.task_reference,
                fints_session_state=updated_session_state_obj.serialize(),
                server_url=snapshot.server_url,
                operation_type=snapshot.operation_type,
                operation_meta=snapshot.operation_meta,
            )
            # Close only the network connection — leave the dialog open at the
            # bank so the next HKTAN process=S message is accepted.
            self._close_connection_only(ctx)
            return ResumeResult(
                status=OperationStatus.PENDING_CONFIRMATION,
                session_state=updated_snapshot.serialize(),
                expires_at=datetime.now(UTC) + timedelta(minutes=5),
            )

        # Approved — parse the response
        payload = self._parse_approved_response(snapshot, response, ctx)
        self._close_context(ctx)
        return ResumeResult(
            status=OperationStatus.COMPLETED,
            result_payload=payload,
        )

    def _parse_approved_response(
        self,
        snapshot: DecoupledSessionSnapshot,
        response,
        ctx,
    ) -> dict[str, object]:
        """Convert approved poll response into a result payload dict.

        For accounts and TAN methods the data is extracted from the context.
        For transactions the bank embeds the result data in the TAN-approval
        response (HICAZ/HITZ segments); these are parsed directly instead of
        making a fresh request that would require a second TAN.
        For balances the accounts are discovered first and then balances are
        fetched through the open dialog.
        """
        from geldstrom.infrastructure.fints.services import FinTSAccountService

        operation_type = snapshot.operation_type

        if operation_type == OperationType.ACCOUNTS:
            service = FinTSAccountService(ctx.credentials)
            discovery = service.discover_from_context(ctx)
            return {"accounts": [_serialize_account(a) for a in discovery.accounts]}

        if operation_type == OperationType.TAN_METHODS:
            from geldstrom.infrastructure.fints.services import FinTSMetadataService

            service = FinTSMetadataService(ctx.credentials)
            methods = service._extract_tan_methods(ctx.parameters)
            return {"methods": [_serialize_tan_method(m) for m in methods]}

        if operation_type == OperationType.TRANSACTIONS:
            from geldstrom.infrastructure.fints.operations.transactions import (
                parse_camt_approved_response,
                parse_mt940_approved_response,
            )

            meta = snapshot.operation_meta
            account_id = meta.get("account_id", "")

            # The bank embeds transaction data in the HKTAN-S approval response;
            # parse it directly to avoid a second request (which would require
            # another TAN on most banks).
            feed = parse_mt940_approved_response(response, account_id)
            if feed.entries:
                return {"transactions": _serialize_transactions(feed)}

            feed = parse_camt_approved_response(response, account_id)
            if feed.entries:
                return {"transactions": _serialize_transactions(feed)}

            # Fallback: re-fetch if data wasn't embedded in the approval response.
            from geldstrom.infrastructure.fints.operations import AccountOperations
            from geldstrom.infrastructure.fints.operations.transactions import (
                CamtFetcher,
                Mt940Fetcher,
            )
            from geldstrom.infrastructure.fints.services import FinTSTransactionService
            from geldstrom.infrastructure.fints.support.helpers import (
                locate_sepa_account,
            )

            start_date_str = meta.get("start_date")
            end_date_str = meta.get("end_date")
            start_date = date.fromisoformat(start_date_str) if start_date_str else None
            end_date = date.fromisoformat(end_date_str) if end_date_str else None

            acct_ops = AccountOperations(ctx.dialog, ctx.parameters)
            sepa_account = locate_sepa_account(acct_ops, account_id)
            mt940 = Mt940Fetcher(ctx.dialog, ctx.parameters)
            camt = CamtFetcher(ctx.dialog, ctx.parameters)
            txn_service = FinTSTransactionService(ctx.credentials)

            feed = txn_service._fetch_with_mt940_preferred(
                mt940,
                camt,
                sepa_account,
                account_id,
                start_date,
                end_date,
            )
            return {"transactions": _serialize_transactions(feed)}

        if operation_type == OperationType.BALANCES:
            from geldstrom.infrastructure.fints.operations import (
                AccountOperations,
                BalanceOperations,
            )
            from geldstrom.infrastructure.fints.services import FinTSBalanceService

            # Discover accounts first (required to find SEPA accounts for balance fetching)
            acct_service = FinTSAccountService(ctx.credentials)
            discovery = acct_service.discover_from_context(ctx)

            balance_ops = BalanceOperations(ctx.dialog, ctx.parameters)
            balance_service = FinTSBalanceService(ctx.credentials)
            acct_ops = AccountOperations(ctx.dialog, ctx.parameters)
            sepa_accounts = acct_ops.fetch_sepa_accounts()
            from geldstrom.infrastructure.fints.support.helpers import account_key

            sepa_lookup = {account_key(s): s for s in sepa_accounts}
            results = []
            for acct in discovery.accounts:
                sepa = sepa_lookup.get(acct.account_id)
                if not sepa:
                    continue
                try:
                    raw = balance_ops.fetch_balance(sepa)
                    results.append(
                        balance_service._balance_from_operations(acct.account_id, raw)
                    )
                except Exception:
                    _logger.debug(
                        "Failed balance for %s", acct.account_id, exc_info=True
                    )
            return {"balances": [_serialize_balance(b) for b in results]}

        return {}

    @staticmethod
    def _close_connection_only(ctx) -> None:
        """Close the network connection without sending HKEND."""
        try:
            if ctx.connection is not None:
                ctx.connection.close()
        except Exception:
            _logger.debug("Error closing connection", exc_info=True)

    @staticmethod
    def _close_context(ctx) -> None:
        """Best-effort close of a resumed dialog context."""
        try:
            if ctx.dialog.is_open:
                ctx.dialog.end()
        except Exception:
            _logger.debug("Error closing resumed dialog", exc_info=True)
        try:
            if ctx.connection is not None:
                ctx.connection.close()
        except Exception:
            _logger.debug("Error closing resumed connection", exc_info=True)

    def _build_client(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
        product_key: str,
        *,
        session_state=None,
    ) -> GeldstromClient:
        gateway_credentials = self._build_gateway_credentials(
            institute, credentials, product_key
        )
        try:
            return self._client_factory.create(
                gateway_credentials, session_state=session_state
            )
        except (
            FinTSClientPINError,
            FinTSClientTemporaryAuthError,
            FinTSSCARequiredError,
            FinTSDialogError,
            FinTSConnectionError,
            FinTSNoResponseError,
            FinTSUnsupportedOperation,
        ) as exc:
            _logger.warning(
                "FinTS bank communication error for %s: %s", institute.blz.value, exc
            )
            raise BankUpstreamUnavailableError("Bank communication failed") from exc
        except Exception as exc:  # pragma: no cover - defensive guard
            raise InternalError(
                "Unexpected failure while creating Geldstrom client"
            ) from exc

    def _build_gateway_credentials(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
        product_key: str,
    ) -> GatewayCredentials:
        if institute.pin_tan_url is None:
            raise BankUpstreamUnavailableError(
                f"Institute {institute.blz.value} does not provide a PIN/TAN endpoint"
            )
        if not institute.pin_tan_url.startswith("https://"):
            raise BankUpstreamUnavailableError(
                f"Institute {institute.blz.value} PIN/TAN endpoint is not HTTPS"
            )
        return GatewayCredentials(
            route=BankRoute(country_code="DE", bank_code=institute.blz.value),
            server_url=institute.pin_tan_url,
            credentials=BankCredentials(
                user_id=credentials.user_id.get_secret_value(),
                secret=SecretStr(credentials.password.get_secret_value()),
                two_factor_method=credentials.tan_method,
                two_factor_device=credentials.tan_medium,
            ),
            product_id=product_key,
            product_version=self._product_version,
        )

    @staticmethod
    def _find_account_by_iban(
        accounts: list[Account], iban: RequestedIban
    ) -> Account | None:
        for account in accounts:
            if account.iban == iban.value:
                return account
        return None


def _serialize_balance(snapshot: BalanceSnapshot) -> dict[str, object]:
    return {
        "account_id": snapshot.account_id,
        "as_of": snapshot.as_of.isoformat(),
        "booked_amount": str(snapshot.booked.amount),
        "booked_currency": snapshot.booked.currency,
        "pending_amount": str(snapshot.pending.amount) if snapshot.pending else None,
        "pending_currency": snapshot.pending.currency if snapshot.pending else None,
        "available_amount": str(snapshot.available.amount)
        if snapshot.available
        else None,
        "available_currency": snapshot.available.currency
        if snapshot.available
        else None,
    }


def _serialize_account(account: Account) -> dict[str, object]:
    owner_name = account.owner.name if isinstance(account.owner, AccountOwner) else None
    capabilities = (
        account.capabilities.as_dict()
        if isinstance(account.capabilities, AccountCapabilities)
        else {}
    )
    return {
        "account_id": account.account_id,
        "iban": account.iban,
        "bic": account.bic,
        "currency": account.currency,
        "product_name": account.product_name,
        "owner_name": owner_name,
        "bank_code": account.bank_route.bank_code,
        "country_code": account.bank_route.country_code,
        "capabilities": dict(capabilities),
        "labels": list(account.raw_labels),
        "metadata": dict(account.metadata),
    }


def _serialize_transactions(feed: TransactionFeed) -> list[dict[str, object]]:
    return [
        _serialize_transaction_entry(feed.account_id, feed, entry)
        for entry in feed.entries
    ]


def _serialize_transaction_entry(
    account_id: str,
    feed: TransactionFeed,
    entry: TransactionEntry,
) -> dict[str, object]:
    amount = (
        entry.amount if isinstance(entry.amount, Decimal) else Decimal(entry.amount)
    )
    return {
        "transaction_id": entry.entry_id,
        "account_id": account_id,
        "booking_date": entry.booking_date.isoformat(),
        "value_date": entry.value_date.isoformat(),
        "amount": str(amount),
        "currency": entry.currency,
        "purpose": entry.purpose,
        "counterpart_name": entry.counterpart_name,
        "counterpart_iban": entry.counterpart_iban,
        "metadata": dict(entry.metadata),
        "feed_start_date": feed.start_date.isoformat(),
        "feed_end_date": feed.end_date.isoformat(),
        "has_more": feed.has_more,
    }


def _serialize_tan_method(method: GeldstromTanMethod) -> TanMethod:
    return TanMethod(
        method_id=method.code,
        display_name=method.name,
        is_decoupled=method.is_decoupled,
    )
