"""Background use case for resuming pending decoupled operations."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Self

from gateway.application.common import IdProvider
from gateway.domain.banking_gateway import (
    BankingConnector,
    OperationSessionStore,
    OperationStatus,
)

from ..dtos.resume_pending_operations import ResumeSummary

if TYPE_CHECKING:
    from gateway.application.ports import ApplicationFactory


class ResumePendingOperationsCommand:
    """Poll pending operation sessions and transition them forward."""

    def __init__(
        self,
        session_store: OperationSessionStore,
        connector: BankingConnector,
        id_provider: IdProvider,
    ) -> None:
        self._session_store = session_store
        self._connector = connector
        self._id_provider = id_provider

    @classmethod
    def from_factory(cls, factory: ApplicationFactory) -> Self:
        return cls(
            session_store=factory.caches.session_store,
            connector=factory.banking_connector,
            id_provider=factory.id_provider,
        )

    async def __call__(self) -> ResumeSummary:
        summary = ResumeSummary()
        now = self._id_provider.now()

        # Purge terminal sessions from previous passes before processing new ones.
        # Running this first ensures clients can still poll a session that was just
        # marked EXPIRED/COMPLETED in the current pass.
        await self._session_store.expire_stale(now)

        for session in await self._session_store.list_all():
            if session.status is not OperationStatus.PENDING_CONFIRMATION:
                continue

            if session.expires_at <= now:
                expired_session = replace(
                    session,
                    status=OperationStatus.EXPIRED,
                    session_state=None,
                )
                await self._session_store.update(expired_session)
                summary = replace(summary, expired_count=summary.expired_count + 1)
                continue

            result = await self._connector.resume_operation(session.session_state)

            if result.status is OperationStatus.PENDING_CONFIRMATION:
                updated_session = replace(
                    session,
                    session_state=result.session_state or session.session_state,
                    expires_at=result.expires_at or session.expires_at,
                    last_polled_at=now,
                )
                await self._session_store.update(updated_session)
                summary = replace(summary, pending_count=summary.pending_count + 1)
                continue

            if result.status is OperationStatus.COMPLETED:
                completed_session = replace(
                    session,
                    status=OperationStatus.COMPLETED,
                    result_payload=result.result_payload,
                    session_state=None,
                    expires_at=result.expires_at or session.expires_at,
                    last_polled_at=now,
                )
                await self._session_store.update(completed_session)
                summary = replace(summary, completed_count=summary.completed_count + 1)
                continue

            if result.status is OperationStatus.FAILED:
                failed_session = replace(
                    session,
                    status=OperationStatus.FAILED,
                    failure_reason=result.failure_reason,
                    session_state=None,
                    expires_at=result.expires_at or session.expires_at,
                    last_polled_at=now,
                )
                await self._session_store.update(failed_session)
                summary = replace(summary, failed_count=summary.failed_count + 1)
                continue

            if result.status is OperationStatus.EXPIRED:
                expired_session = replace(
                    session,
                    status=OperationStatus.EXPIRED,
                    session_state=None,
                    expires_at=result.expires_at or session.expires_at,
                    last_polled_at=now,
                )
                await self._session_store.update(expired_session)
                summary = replace(summary, expired_count=summary.expired_count + 1)

        return summary
