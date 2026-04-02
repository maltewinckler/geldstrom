"""Fetch transaction history through the gateway application layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import TYPE_CHECKING, Self

from gateway.application.common import (
    IdProvider,
    InstitutionNotFoundError,
    ValidationError,
    cap_session_expires_at,
)
from gateway.application.consumer.queries.authenticate_consumer import (
    AuthenticateConsumerQuery,
)
from gateway.domain import DomainError
from gateway.domain.banking_gateway import (
    BankingConnector,
    BankLeitzahl,
    BankProtocol,
    FinTSInstituteRepository,
    OperationSessionStore,
    OperationStatus,
    OperationType,
    PendingOperationSession,
    PresentedBankCredentials,
    RequestedIban,
)

from ..dtos.fetch_transactions import TransactionsResultEnvelope

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
    tan_method: str | None = None
    tan_medium: str | None = None

    @property
    def validated_iban(self) -> RequestedIban:
        try:
            return RequestedIban(self.iban)
        except DomainError as exc:
            raise ValidationError(str(exc)) from exc


class FetchTransactionsCommand:
    """Authenticate, validate, and execute a transaction-history request."""

    def __init__(
        self,
        authenticate_consumer: AuthenticateConsumerQuery,
        institute_catalog: FinTSInstituteRepository,
        connector: BankingConnector,
        session_store: OperationSessionStore,
        id_provider: IdProvider,
        ttl_seconds: int = 120,
    ) -> None:
        self._authenticate_consumer = authenticate_consumer
        self._institute_catalog = institute_catalog
        self._connector = connector
        self._session_store = session_store
        self._id_provider = id_provider
        self._ttl_seconds = ttl_seconds

    @classmethod
    def from_factory(cls, factory: ApplicationFactory) -> Self:
        return cls(
            authenticate_consumer=AuthenticateConsumerQuery.from_factory(factory),
            institute_catalog=factory.caches.institute,
            connector=factory.banking_connector,
            session_store=factory.caches.session_store,
            id_provider=factory.id_provider,
            ttl_seconds=factory.operation_session_ttl_seconds,
        )

    async def __call__(
        self,
        request: FetchTransactionsInput,
        presented_api_key: str,
    ) -> TransactionsResultEnvelope:
        authenticated_consumer = await self._authenticate_consumer(presented_api_key)
        credentials = PresentedBankCredentials(
            user_id=request.user_id,
            password=request.password,
            tan_method=request.tan_method,
            tan_medium=request.tan_medium,
        )

        institute = await self._institute_catalog.get_by_blz(request.blz)
        if institute is None:
            raise InstitutionNotFoundError(f"No institute found for BLZ {request.blz}")

        start_date, end_date = self._resolve_date_range(request)
        result = await self._connector.fetch_transactions(
            institute,
            credentials,
            request.validated_iban,
            start_date,
            end_date,
        )

        if result.status is OperationStatus.PENDING_CONFIRMATION:
            operation_id = self._id_provider.new_operation_id()
            created_at = self._id_provider.now()
            expires_at = cap_session_expires_at(
                result.expires_at, created_at, self._ttl_seconds
            )
            session = PendingOperationSession(
                operation_id=operation_id,
                consumer_id=authenticated_consumer,
                protocol=request.protocol,
                operation_type=OperationType.TRANSACTIONS,
                session_state=result.session_state,
                status=OperationStatus.PENDING_CONFIRMATION,
                created_at=created_at,
                expires_at=expires_at,
            )
            await self._session_store.create(session)
            return TransactionsResultEnvelope(
                status=result.status,
                operation_id=operation_id,
                expires_at=expires_at,
            )

        return TransactionsResultEnvelope(
            status=result.status,
            transactions=list(result.transactions),
            failure_reason=result.failure_reason,
        )

    def _resolve_date_range(self, request: FetchTransactionsInput) -> tuple[date, date]:
        end_date = request.end_date or self._id_provider.now().date()
        start_date = request.start_date or (end_date - timedelta(days=90))
        if start_date > end_date:
            raise ValidationError("start_date must be on or before end_date")
        if (end_date - start_date).days > 365:
            raise ValidationError("Date range must not exceed 365 days")
        return start_date, end_date
