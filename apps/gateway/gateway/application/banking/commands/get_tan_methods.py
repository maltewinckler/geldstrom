"""Fetch allowed TAN methods through the gateway application layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Self

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

from ..dtos.get_tan_methods import TanMethodsResultEnvelope

if TYPE_CHECKING:
    from gateway.application.ports import ApplicationFactory


@dataclass(frozen=True)
class GetTanMethodsInput:
    """Input payload for fetching allowed TAN methods."""

    protocol: BankProtocol
    blz: BankLeitzahl
    user_id: str
    password: str
    tan_method: str | None = None
    tan_medium: str | None = None


class GetTanMethodsCommand:
    """Authenticate, validate, and fetch decoupled-only TAN methods."""

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
        self, request: GetTanMethodsInput, presented_api_key: str
    ) -> TanMethodsResultEnvelope:
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

        result = await self._connector.get_tan_methods(institute, credentials)

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
                operation_type=OperationType.TAN_METHODS,
                session_state=result.session_state,
                status=OperationStatus.PENDING_CONFIRMATION,
                created_at=created_at,
                expires_at=expires_at,
            )
            await self._session_store.create(session)
            return TanMethodsResultEnvelope(
                status=result.status,
                operation_id=operation_id,
                expires_at=expires_at,
            )

        allowed_methods = [method for method in result.methods if method.is_decoupled]
        return TanMethodsResultEnvelope(
            status=result.status,
            methods=allowed_methods,
            failure_reason=result.failure_reason,
        )
