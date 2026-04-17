"""In-memory fake AuditService for application tests."""

from __future__ import annotations

from uuid import UUID

from gateway.domain.audit import AuditEventType


class FakeAuditService:
    """Captures recorded audit events without touching any repository."""

    def __init__(self) -> None:
        self.recorded: list[tuple[AuditEventType, UUID | None]] = []

    async def record(
        self, event_type: AuditEventType, consumer_id: UUID | None
    ) -> None:
        self.recorded.append((event_type, consumer_id))
