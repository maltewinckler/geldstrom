"""Geldstrom-backed implementation of the gateway banking connector."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

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
from geldstrom.clients.fints3_decoupled import FinTS3ClientDecoupled, PollResult
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
from geldstrom.domain import TANMethod as GeldstromTanMethod
from geldstrom.domain.connection.challenge import DecoupledTANPending
from geldstrom.infrastructure.fints import (
    FinTSClientPINError,
    FinTSClientTemporaryAuthError,
    FinTSConnectionError,
    FinTSDialogError,
    FinTSNoResponseError,
    FinTSSCARequiredError,
    FinTSUnsupportedOperation,
    GatewayCredentials,
)

from .exceptions import GeldstromPendingConfirmation
from .models import GeldstromClient, GeldstromClientFactory, SerializedPendingOperation
from .registry import PendingClientRegistry, PendingHandle
from .serialization import (
    deserialize_fints_session_state,
    deserialize_pending_operation,
    serialize_fints_session_state,
    serialize_pending_operation,
)

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
        pending_registry: PendingClientRegistry | None = None,
    ) -> None:
        self._product_key = product_key
        self._product_version = product_version
        self._client_factory = client_factory or _DefaultGeldstromClientFactory()
        self._pending_registry = pending_registry or PendingClientRegistry()

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

    async def resume_operation(self, session_state: bytes) -> ResumeResult:
        # Check if this is an in-memory handle (DecoupledTANPending flow)
        handle_id = self._extract_handle_id(session_state)
        if handle_id is not None:
            return await asyncio.to_thread(self._resume_from_registry, handle_id)

        # Legacy path: deserialize full FinTS session state
        product_key = self._product_key
        try:
            pending_state = deserialize_pending_operation(session_state)
            restored_session = deserialize_fints_session_state(
                pending_state.fints_session_state
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            raise InternalError(
                "Unable to deserialize pending banking session state"
            ) from exc

        return await asyncio.to_thread(
            self._resume_operation_sync,
            pending_state,
            restored_session,
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
            return self._store_pending_handle(
                client, OperationType.ACCOUNTS, AccountsResult
            )
        except GeldstromPendingConfirmation as pending:
            return AccountsResult(
                status=OperationStatus.PENDING_CONFIRMATION,
                session_state=self._serialize_pending_state(
                    operation_type=OperationType.ACCOUNTS,
                    institute=institute,
                    credentials=credentials,
                    session_state=pending.session_state,
                ),
                expires_at=pending.expires_at,
            )
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
            return self._store_pending_handle(
                client, OperationType.TRANSACTIONS, TransactionsResult
            )
        except GeldstromPendingConfirmation as pending:
            return TransactionsResult(
                status=OperationStatus.PENDING_CONFIRMATION,
                session_state=self._serialize_pending_state(
                    operation_type=OperationType.TRANSACTIONS,
                    institute=institute,
                    credentials=credentials,
                    session_state=pending.session_state,
                    iban=iban.value,
                    start_date=start_date,
                    end_date=end_date,
                ),
                expires_at=pending.expires_at,
            )
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
            return self._store_pending_handle(
                client, OperationType.BALANCES, BalancesResult
            )
        except GeldstromPendingConfirmation as pending:
            return BalancesResult(
                status=OperationStatus.PENDING_CONFIRMATION,
                session_state=self._serialize_pending_state(
                    operation_type=OperationType.BALANCES,
                    institute=institute,
                    credentials=credentials,
                    session_state=pending.session_state,
                ),
                expires_at=pending.expires_at,
            )
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
            return self._store_pending_handle(
                client, OperationType.TAN_METHODS, TanMethodsResult
            )
        except GeldstromPendingConfirmation as pending:
            return TanMethodsResult(
                status=OperationStatus.PENDING_CONFIRMATION,
                session_state=self._serialize_pending_state(
                    operation_type=OperationType.TAN_METHODS,
                    institute=institute,
                    credentials=credentials,
                    session_state=pending.session_state,
                ),
                expires_at=pending.expires_at,
            )
        return TanMethodsResult(
            status=OperationStatus.COMPLETED,
            methods=[_serialize_tan_method(method) for method in methods],
        )

    def _store_pending_handle(
        self,
        client,
        operation_type: OperationType,
        result_cls: type,
        *,
        extra_meta: dict | None = None,
    ):
        """Store a live client in the registry and return a PENDING result."""
        handle_id = str(uuid4())
        expires_at = datetime.now(UTC) + timedelta(minutes=5)
        self._pending_registry.store(
            handle_id,
            PendingHandle(
                client=client,
                operation_type=operation_type,
                expires_at=expires_at,
                extra_meta=extra_meta or {},
            ),
        )
        session_state = json.dumps({"handle": handle_id}).encode()
        return result_cls(
            status=OperationStatus.PENDING_CONFIRMATION,
            session_state=session_state,
            expires_at=expires_at,
        )

    @staticmethod
    def _extract_handle_id(session_state: bytes) -> str | None:
        """Return the handle ID if session_state is an in-memory handle marker."""
        try:
            parsed = json.loads(session_state)
            if isinstance(parsed, dict) and "handle" in parsed:
                return parsed["handle"]
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
        return None

    def _resume_from_registry(self, handle_id: str) -> ResumeResult:
        """Poll one round for a pending TAN stored in the in-memory registry."""
        handle = self._pending_registry.get(handle_id)
        if handle is None:
            return ResumeResult(
                status=OperationStatus.EXPIRED,
                failure_reason="Pending operation expired or server restarted",
            )

        result: PollResult = handle.client.poll_tan()

        if result.status == "pending":
            session_state = json.dumps({"handle": handle_id}).encode()
            return ResumeResult(
                status=OperationStatus.PENDING_CONFIRMATION,
                session_state=session_state,
                expires_at=handle.expires_at,
            )

        if result.status == "approved":
            self._pending_registry.remove(handle_id)
            payload = self._approved_result_payload(handle.operation_type, result.data)
            return ResumeResult(
                status=OperationStatus.COMPLETED,
                result_payload=payload,
            )

        # failed / expired
        self._pending_registry.remove(handle_id)
        return ResumeResult(
            status=OperationStatus.FAILED,
            failure_reason=result.error or "TAN verification failed",
        )

    def _approved_result_payload(
        self, operation_type: OperationType, data
    ) -> dict[str, object]:
        """Convert approved PollResult.data into a ResumeResult payload dict."""
        if operation_type is OperationType.TRANSACTIONS:
            if isinstance(data, TransactionFeed):
                return {"transactions": _serialize_transactions(data)}
            return {"transactions": []}

        if operation_type is OperationType.ACCOUNTS:
            if isinstance(data, (list, tuple)):
                return {"accounts": [_serialize_account(a) for a in data]}
            return {"accounts": []}

        if operation_type is OperationType.BALANCES:
            if isinstance(data, (list, tuple)):
                return {"balances": [_serialize_balance(b) for b in data]}
            return {"balances": []}

        if operation_type is OperationType.TAN_METHODS:
            if isinstance(data, (list, tuple)):
                return {"methods": [_serialize_tan_method(m) for m in data]}
            return {"methods": []}

        return {}

    def _resume_operation_sync(
        self,
        pending_state: SerializedPendingOperation,
        restored_session,
        product_key: str,
    ) -> ResumeResult:
        institute = FinTSInstitute(
            blz=type(self)._bank_leitzahl(pending_state.bank_code),
            bic=None,
            name="resumed-session",
            city=None,
            organization=None,
            pin_tan_url=pending_state.endpoint or None,
            fints_version=None,
            last_source_update=None,
        )
        credentials = PresentedBankCredentials(
            user_id=pending_state.user_id,
            password=pending_state.password,
        )
        client = self._build_client(
            institute,
            credentials,
            product_key,
            session_state=restored_session,
        )

        try:
            if pending_state.operation_type is OperationType.BALANCES:
                balances = client.get_balances()
                return ResumeResult(
                    status=OperationStatus.COMPLETED,
                    result_payload={
                        "balances": [_serialize_balance(b) for b in balances]
                    },
                )
            if pending_state.operation_type is OperationType.ACCOUNTS:
                accounts = client.list_accounts()
                return ResumeResult(
                    status=OperationStatus.COMPLETED,
                    result_payload={
                        "accounts": [
                            _serialize_account(account) for account in accounts
                        ]
                    },
                )
            if pending_state.operation_type is OperationType.TRANSACTIONS:
                account = self._find_account_by_iban(
                    client.list_accounts(),
                    RequestedIban(pending_state.iban or ""),
                )
                if account is None:
                    return ResumeResult(
                        status=OperationStatus.FAILED,
                        failure_reason=(
                            f"No account found for IBAN {pending_state.iban}"
                        ),
                    )
                feed = client.get_transactions(
                    account,
                    start_date=pending_state.start_date,
                    end_date=pending_state.end_date,
                )
                return ResumeResult(
                    status=OperationStatus.COMPLETED,
                    result_payload={"transactions": _serialize_transactions(feed)},
                )
            if pending_state.operation_type is OperationType.TAN_METHODS:
                methods = client.get_tan_methods()
                return ResumeResult(
                    status=OperationStatus.COMPLETED,
                    result_payload={
                        "methods": [_serialize_tan_method(method) for method in methods]
                    },
                )
        except GeldstromPendingConfirmation as pending:
            return ResumeResult(
                status=OperationStatus.PENDING_CONFIRMATION,
                session_state=self._serialize_pending_state(
                    operation_type=pending_state.operation_type,
                    institute=institute,
                    credentials=credentials,
                    session_state=pending.session_state,
                    iban=pending_state.iban,
                    start_date=pending_state.start_date,
                    end_date=pending_state.end_date,
                ),
                expires_at=pending.expires_at,
            )

        raise InternalError(
            f"Unsupported pending operation type: {pending_state.operation_type}"
        )

    def _build_client(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
        product_key: str,
        *,
        session_state=None,
    ) -> GeldstromClient:
        if institute.pin_tan_url is None:
            raise BankUpstreamUnavailableError(
                f"Institute {institute.blz.value} does not provide a PIN/TAN endpoint"
            )
        if not institute.pin_tan_url.startswith("https://"):
            raise BankUpstreamUnavailableError(
                f"Institute {institute.blz.value} PIN/TAN endpoint is not HTTPS"
            )
        gateway_credentials = GatewayCredentials(
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

    def _serialize_pending_state(
        self,
        *,
        operation_type: OperationType,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
        session_state,
        iban: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> bytes:
        return serialize_pending_operation(
            SerializedPendingOperation(
                operation_type=operation_type,
                bank_code=institute.blz.value,
                endpoint=institute.pin_tan_url if institute.pin_tan_url else "",
                user_id=credentials.user_id.get_secret_value(),
                password=credentials.password.get_secret_value(),
                iban=iban,
                start_date=start_date,
                end_date=end_date,
                fints_session_state=serialize_fints_session_state(session_state),
            )
        )

    @staticmethod
    def _find_account_by_iban(
        accounts: list[Account], iban: RequestedIban
    ) -> Account | None:
        for account in accounts:
            if account.iban == iban.value:
                return account
        return None

    @staticmethod
    def _bank_leitzahl(value: str):
        from gateway.domain.banking_gateway import BankLeitzahl

        return BankLeitzahl(value)


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
