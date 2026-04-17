"""AuditService — fire-and-forget audit event recorder."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Self
from uuid import UUID

from gateway.application.common import IdProvider
from gateway.domain.audit import AuditEvent, AuditEventType, AuditRepository

if TYPE_CHECKING:
    from gateway.application.ports import ApplicationFactory

_logger = logging.getLogger(__name__)


class AuditService:
    """Records audit events; absorbs all repository errors."""

    def __init__(self, repo: AuditRepository, id_provider: IdProvider) -> None:
        self._repo = repo
        self._id_provider = id_provider

    @classmethod
    def from_factory(cls, factory: ApplicationFactory) -> Self:
        return cls(factory.audit_repository, factory.id_provider)

    async def record(
        self, event_type: AuditEventType, consumer_id: UUID | None
    ) -> None:
        event = AuditEvent(
            event_id=UUID(self._id_provider.new_operation_id()),
            event_type=event_type,
            consumer_id=consumer_id,
            occurred_at=datetime.now(UTC),
        )
        try:
            await self._repo.append(event)
        except Exception:
            _logger.error(
                "Failed to persist audit event",
                extra={
                    "event_type": event_type,
                    "consumer_id": str(consumer_id) if consumer_id else None,
                },
                exc_info=True,
            )
