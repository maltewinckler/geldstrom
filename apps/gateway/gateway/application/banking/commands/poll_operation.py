"""Poll a pending decoupled operation with fresh bank credentials."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from pydantic import BaseModel

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
    FinTSInstituteRepository,
    OperationSessionStore,
    OperationStatus,
    OperationType,
    PresentedBankCredentials,
)

if TYPE_CHECKING:
    from gateway.application.ports import ApplicationFactory


class PollOperationInput(BaseModel, frozen=True):
    blz: BankLeitzahl
    user_id: str
    password: str
    tan_method: str | None = None
    tan_medium: str | None = None


class PollOperationResult(BaseModel, frozen=True):
    status: str
    operation_id: str
    operation_type: OperationType | None = None
    result_payload: dict | None = None
    failure_reason: str | None = None
    expires_at: object | None = None


class PollOperationCommand:
    """Authenticate, look up the pending session, and poll with fresh credentials."""

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
        operation_id: str,
        request: PollOperationInput,
        presented_api_key: str,
    ) -> PollOperationResult:
        consumer_id = await self._authenticate_consumer(presented_api_key)

        session = await self._session_store.get(operation_id)
        if session is None:
            # Security: return EXPIRED rather than NOT_FOUND to avoid an
            # enumeration oracle. A caller that can distinguish "this ID never
            # existed" from "this ID belongs to someone else" could probe for
            # valid operation IDs belonging to other consumers.
            return PollOperationResult(
                status=OperationStatus.EXPIRED,
                operation_id=operation_id,
            )
        if session.consumer_id != consumer_id:
            # Security: same EXPIRED response as above — intentionally
            # indistinguishable from the "not found" case.
            return PollOperationResult(
                status=OperationStatus.EXPIRED,
                operation_id=operation_id,
            )
        if session.status != OperationStatus.PENDING_CONFIRMATION:
            return PollOperationResult(
                status=session.status,
                operation_id=operation_id,
                operation_type=session.operation_type,
                result_payload=session.result_payload,
                failure_reason=session.failure_reason,
            )

        institute = await self._institute_catalog.get_by_blz(request.blz)
        if institute is None:
            raise InstitutionNotFoundError(f"No institute found for BLZ {request.blz}")

        credentials = PresentedBankCredentials(
            user_id=request.user_id,
            password=request.password,
            tan_method=request.tan_method,
            tan_medium=request.tan_medium,
        )

        result = await self._connector.resume_operation(
            session.session_state, credentials, institute
        )

        now = self._id_provider.now()

        if result.status is OperationStatus.PENDING_CONFIRMATION:
            expires_at = cap_session_expires_at(
                result.expires_at, session.created_at, self._ttl_seconds
            )
            updated = session.model_copy(
                update={
                    "session_state": result.session_state or session.session_state,
                    "expires_at": expires_at,
                    "last_polled_at": now,
                }
            )
            await self._session_store.update(updated)
            return PollOperationResult(
                status=OperationStatus.PENDING_CONFIRMATION,
                operation_id=operation_id,
                operation_type=session.operation_type,
                expires_at=expires_at,
            )

        if result.status is OperationStatus.COMPLETED:
            completed = session.model_copy(
                update={
                    "status": OperationStatus.COMPLETED,
                    "result_payload": result.result_payload,
                    "session_state": None,
                    "last_polled_at": now,
                }
            )
            await self._session_store.update(completed)
            return PollOperationResult(
                status=OperationStatus.COMPLETED,
                operation_id=operation_id,
                operation_type=session.operation_type,
                result_payload=result.result_payload,
            )

        # FAILED
        failed = session.model_copy(
            update={
                "status": OperationStatus.FAILED,
                "failure_reason": result.failure_reason,
                "session_state": None,
                "last_polled_at": now,
            }
        )
        await self._session_store.update(failed)
        return PollOperationResult(
            status=OperationStatus.FAILED,
            operation_id=operation_id,
            operation_type=session.operation_type,
            failure_reason=result.failure_reason,
        )
