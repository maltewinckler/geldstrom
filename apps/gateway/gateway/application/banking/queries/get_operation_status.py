"""Read pending-operation status through the gateway application layer."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from gateway.application.banking.dtos.get_operation_status import (
    OperationStatusEnvelope,
)
from gateway.application.common import (
    ForbiddenError,
    IdProvider,
    OperationNotFoundError,
)
from gateway.application.consumer.queries.authenticate_consumer import (
    AuthenticateConsumerQuery,
)
from gateway.domain.banking_gateway import OperationSessionStore, OperationStatus

if TYPE_CHECKING:
    from gateway.application.ports import ApplicationFactory


class GetOperationStatusQuery:
    """Authenticate and expose operation state for one consumer-owned session."""

    def __init__(
        self,
        authenticate_consumer: AuthenticateConsumerQuery,
        session_store: OperationSessionStore,
        id_provider: IdProvider,
    ) -> None:
        self._authenticate_consumer = authenticate_consumer
        self._session_store = session_store
        self._id_provider = id_provider

    @classmethod
    def from_factory(cls, factory: ApplicationFactory) -> Self:
        return cls(
            authenticate_consumer=AuthenticateConsumerQuery.from_factory(factory),
            session_store=factory.caches.session_store,
            id_provider=factory.id_provider,
        )

    async def __call__(
        self, operation_id: str, presented_api_key: str
    ) -> OperationStatusEnvelope:
        authenticated_consumer = await self._authenticate_consumer(presented_api_key)
        session = await self._session_store.get(operation_id)
        if session is None:
            raise OperationNotFoundError(f"No operation found for id {operation_id}")

        if session.consumer_id != authenticated_consumer:
            raise ForbiddenError(
                "Operation does not belong to the authenticated consumer"
            )

        if session.status is OperationStatus.PENDING_CONFIRMATION:
            now = self._id_provider.now()
            if session.expires_at <= now:
                return OperationStatusEnvelope(
                    status=OperationStatus.EXPIRED,
                    operation_id=operation_id,
                    operation_type=session.operation_type,
                    expires_at=session.expires_at,
                )

        if session.status is OperationStatus.COMPLETED:
            return OperationStatusEnvelope(
                status=session.status,
                operation_id=operation_id,
                operation_type=session.operation_type,
                result_payload=session.result_payload,
                expires_at=session.expires_at,
            )

        if session.status is OperationStatus.FAILED:
            return OperationStatusEnvelope(
                status=session.status,
                operation_id=operation_id,
                operation_type=session.operation_type,
                failure_reason=session.failure_reason,
                expires_at=session.expires_at,
            )

        if session.status is OperationStatus.EXPIRED:
            return OperationStatusEnvelope(
                status=session.status,
                operation_id=operation_id,
                operation_type=session.operation_type,
                expires_at=session.expires_at,
            )

        return OperationStatusEnvelope(
            status=session.status,
            operation_id=operation_id,
            operation_type=session.operation_type,
            expires_at=session.expires_at,
        )
