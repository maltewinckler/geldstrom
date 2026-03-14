"""Fetch transaction history through the gateway application layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING, Self

from pydantic import SecretStr

from gateway.application.auth.queries.authenticate_consumer import (
    AuthenticateConsumerQuery,
)
from gateway.application.common import (
    IdProvider,
    InstitutionNotFoundError,
    UnsupportedProtocolError,
    ValidationError,
)
from gateway.application.product_registration.ports.current_product_key import (
    CurrentProductKeyProvider,
)
from gateway.domain.banking_gateway import (
    BankingConnector,
    BankRequestSanitizationPolicy,
    OperationSessionStore,
    OperationStatus,
    PendingOperationSession,
    PresentedBankCredentials,
    PresentedBankPassword,
    PresentedBankUserId,
    RequestedIban,
)
from gateway.domain.institution_catalog import BankLeitzahl
from gateway.domain.shared import BankProtocol

from ..dtos.fetch_transactions import TransactionsResultEnvelope
from ..ports.institute_catalog import InstituteCatalogPort

if TYPE_CHECKING:
    from gateway.application.ports import ApplicationFactory


@dataclass(frozen=True)
class FetchTransactionsInput:
    """Input payload for fetching historical transactions."""

    protocol: BankProtocol
    blz: BankLeitzahl
    user_id: str
    password: str
    iban: str
    start_date: date | None = None
    end_date: date | None = None


class FetchTransactionsCommand:
    """Authenticate, validate, and execute a transaction-history request."""

    def __init__(
        self,
        authenticate_consumer: AuthenticateConsumerQuery,
        institute_catalog: InstituteCatalogPort,
        current_product_key_provider: CurrentProductKeyProvider,
        connector: BankingConnector,
        session_store: OperationSessionStore,
        id_provider: IdProvider,
    ) -> None:
        self._authenticate_consumer = authenticate_consumer
        self._institute_catalog = institute_catalog
        self._current_product_key_provider = current_product_key_provider
        self._connector = connector
        self._session_store = session_store
        self._id_provider = id_provider

    @classmethod
    def from_factory(cls, factory: ApplicationFactory) -> Self:
        return cls(
            authenticate_consumer=AuthenticateConsumerQuery.from_factory(factory),
            institute_catalog=factory.caches.institute,
            current_product_key_provider=factory.caches.product_key,
            connector=factory.banking_connector,
            session_store=factory.caches.session_store,
            id_provider=factory.id_provider,
        )

    async def __call__(
        self,
        request: FetchTransactionsInput,
        presented_api_key: str,
    ) -> TransactionsResultEnvelope:
        if request.protocol is not BankProtocol.FINTS:
            raise UnsupportedProtocolError(
                f"Unsupported banking protocol: {request.protocol.value}"
            )

        authenticated_consumer = await self._authenticate_consumer(presented_api_key)
        credentials = PresentedBankCredentials(
            user_id=PresentedBankUserId(SecretStr(request.user_id)),
            password=PresentedBankPassword(SecretStr(request.password)),
        )
        BankRequestSanitizationPolicy.sanitize(credentials)

        institute = await self._institute_catalog.get_by_blz(request.blz)
        if institute is None:
            raise InstitutionNotFoundError(f"No institute found for BLZ {request.blz}")

        await self._current_product_key_provider.require_current()
        start_date, end_date = self._resolve_date_range(request)
        result = await self._connector.fetch_transactions(
            institute,
            credentials,
            RequestedIban(request.iban),
            start_date,
            end_date,
        )

        if result.status is OperationStatus.PENDING_CONFIRMATION:
            operation_id = self._id_provider.new_operation_id()
            created_at = self._id_provider.now()
            session = PendingOperationSession(
                operation_id=operation_id,
                consumer_id=authenticated_consumer.consumer_id,
                protocol=request.protocol,
                operation_type="transactions",
                session_state=result.session_state,
                status=OperationStatus.PENDING_CONFIRMATION,
                created_at=created_at,
                expires_at=result.expires_at,
            )
            await self._session_store.create(session)
            return TransactionsResultEnvelope(
                status=result.status,
                operation_id=operation_id,
                expires_at=result.expires_at,
            )

        return TransactionsResultEnvelope(
            status=result.status,
            transactions=list(result.transactions),
            failure_reason=result.failure_reason,
        )

    def _resolve_date_range(
        self, request: FetchTransactionsInput
    ) -> tuple[date, date]:
        end_date = request.end_date or self._id_provider.now().date()
        start_date = request.start_date or (end_date - timedelta(days=90))
        if start_date > end_date:
            raise ValidationError("start_date must be on or before end_date")
        return start_date, end_date
