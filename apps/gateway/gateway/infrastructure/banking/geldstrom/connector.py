"""Geldstrom-backed implementation of the gateway banking connector."""

from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal

from pydantic import SecretStr

from gateway.application.common import BankUpstreamUnavailableError, InternalError
from gateway.application.product_registration import CurrentProductKeyProvider
from gateway.domain.banking_gateway import (
    AccountsResult,
    BankingConnector,
    OperationStatus,
    ResumeResult,
    TanMethod,
    TanMethodsResult,
    TransactionsResult,
)
from gateway.domain.banking_gateway.value_objects import (
    PresentedBankCredentials,
    RequestedIban,
)
from gateway.domain.institution_catalog import FinTSInstitute
from geldstrom.clients import FinTS3Client
from geldstrom.domain import (
    Account,
    AccountCapabilities,
    AccountOwner,
    BankCredentials,
    BankRoute,
    TransactionEntry,
    TransactionFeed,
)
from geldstrom.domain import TANMethod as GeldstromTanMethod
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
from .serialization import (
    deserialize_fints_session_state,
    deserialize_pending_operation,
    serialize_fints_session_state,
    serialize_pending_operation,
)


class _DefaultGeldstromClientFactory(GeldstromClientFactory):
    def create(
        self,
        credentials: GatewayCredentials,
        session_state=None,
    ) -> GeldstromClient:
        return FinTS3Client.from_gateway_credentials(
            credentials,
            session_state=session_state,
        )


class GeldstromBankingConnector(BankingConnector):
    """Translate gateway banking operations to Geldstrom calls."""

    def __init__(
        self,
        current_product_key_provider: CurrentProductKeyProvider,
        *,
        product_version: str,
        client_factory: GeldstromClientFactory | None = None,
    ) -> None:
        self._current_product_key_provider = current_product_key_provider
        self._product_version = product_version
        self._client_factory = client_factory or _DefaultGeldstromClientFactory()

    async def list_accounts(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
    ) -> AccountsResult:
        product_key = await self._current_product_key_provider.require_current()
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
        product_key = await self._current_product_key_provider.require_current()
        return await asyncio.to_thread(
            self._fetch_transactions_sync,
            institute,
            credentials,
            iban,
            start_date,
            end_date,
            product_key,
        )

    async def get_tan_methods(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
    ) -> TanMethodsResult:
        product_key = await self._current_product_key_provider.require_current()
        return await asyncio.to_thread(
            self._get_tan_methods_sync,
            institute,
            credentials,
            product_key,
        )

    async def resume_operation(self, session_state: bytes) -> ResumeResult:
        product_key = await self._current_product_key_provider.require_current()
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
        except GeldstromPendingConfirmation as pending:
            return AccountsResult(
                status=OperationStatus.PENDING_CONFIRMATION,
                session_state=self._serialize_pending_state(
                    operation_type="accounts",
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
        except GeldstromPendingConfirmation as pending:
            return TransactionsResult(
                status=OperationStatus.PENDING_CONFIRMATION,
                session_state=self._serialize_pending_state(
                    operation_type="transactions",
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

    def _get_tan_methods_sync(
        self,
        institute: FinTSInstitute,
        credentials: PresentedBankCredentials,
        product_key: str,
    ) -> TanMethodsResult:
        client = self._build_client(institute, credentials, product_key)
        try:
            methods = client.get_tan_methods()
        except GeldstromPendingConfirmation as pending:
            return TanMethodsResult(
                status=OperationStatus.PENDING_CONFIRMATION,
                session_state=self._serialize_pending_state(
                    operation_type="tan_methods",
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
            pin_tan_url=type(self)._endpoint(pending_state.endpoint),
            fints_version=None,
            last_source_update=None,
            source_row_checksum="resumed-session",
            source_payload={},
        )
        credentials = PresentedBankCredentials(
            user_id=type(self)._user_id(pending_state.user_id),
            password=type(self)._password(pending_state.password),
        )
        client = self._build_client(
            institute,
            credentials,
            product_key,
            session_state=restored_session,
        )

        try:
            if pending_state.operation_type == "accounts":
                accounts = client.list_accounts()
                return ResumeResult(
                    status=OperationStatus.COMPLETED,
                    result_payload={
                        "accounts": [
                            _serialize_account(account) for account in accounts
                        ]
                    },
                )
            if pending_state.operation_type == "transactions":
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
            if pending_state.operation_type == "tan_methods":
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
        gateway_credentials = GatewayCredentials(
            route=BankRoute(country_code="DE", bank_code=institute.blz.value),
            server_url=institute.pin_tan_url.value,
            credentials=BankCredentials(
                user_id=credentials.user_id.value.get_secret_value(),
                secret=SecretStr(credentials.password.value.get_secret_value()),
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
            raise BankUpstreamUnavailableError(str(exc)) from exc
        except Exception as exc:  # pragma: no cover - defensive guard
            raise InternalError(
                "Unexpected failure while creating Geldstrom client"
            ) from exc

    def _serialize_pending_state(
        self,
        *,
        operation_type: str,
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
                endpoint=institute.pin_tan_url.value if institute.pin_tan_url else "",
                user_id=credentials.user_id.value.get_secret_value(),
                password=credentials.password.value.get_secret_value(),
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
        from gateway.domain.institution_catalog import BankLeitzahl

        return BankLeitzahl(value)

    @staticmethod
    def _endpoint(value: str):
        from gateway.domain.institution_catalog import InstituteEndpoint

        return InstituteEndpoint(value)

    @staticmethod
    def _user_id(value: str):
        from gateway.domain.banking_gateway import PresentedBankUserId

        return PresentedBankUserId(SecretStr(value))

    @staticmethod
    def _password(value: str):
        from gateway.domain.banking_gateway import PresentedBankPassword

        return PresentedBankPassword(SecretStr(value))


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
