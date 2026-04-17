"""Fetch account balances through the gateway application layer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from pydantic import BaseModel

from gateway.application.banking.dtos.get_balances import BalancesResultEnvelope
from gateway.application.common import (
    IdProvider,
    InstitutionNotFoundError,
    cap_session_expires_at,
)
from gateway.application.consumer.queries.authenticate_consumer import (
    AuthenticateConsumerQuery,
)
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
)

if TYPE_CHECKING:
    from gateway.application.ports import ApplicationFactory


class GetBalancesInput(BaseModel, frozen=True):
    """Input payload for fetching account balances."""

    protocol: BankProtocol
    blz: BankLeitzahl
    user_id: str
    password: str
    tan_method: str | None = None
    tan_medium: str | None = None


class GetBalancesCommand:
    """Authenticate, validate, and execute a balance-query request."""

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
        self, request: GetBalancesInput, presented_api_key: str
    ) -> BalancesResultEnvelope:
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

        result = await self._connector.get_balances(institute, credentials)

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
                operation_type=OperationType.BALANCES,
                session_state=result.session_state,
                status=OperationStatus.PENDING_CONFIRMATION,
                created_at=created_at,
                expires_at=expires_at,
            )
            await self._session_store.create(session)
            return BalancesResultEnvelope(
                status=result.status,
                operation_id=operation_id,
                expires_at=expires_at,
            )

        return BalancesResultEnvelope(
            status=result.status,
            balances=list(result.balances),
            failure_reason=result.failure_reason,
        )
