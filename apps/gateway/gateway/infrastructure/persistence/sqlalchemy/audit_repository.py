"""SQL repository for audit events (write-only)."""

from __future__ import annotations

from gateway_contracts.schema import audit_events_table
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncEngine

from gateway.domain.audit import AuditEvent, AuditRepository


class AuditRepositorySqlAlchemy(AuditRepository):
    """Persist audit events as immutable rows in the audit_events table."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def append(self, event: AuditEvent) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                insert(audit_events_table).values(
                    event_id=event.event_id,
                    event_type=event.event_type.value,
                    consumer_id=event.consumer_id,
                    occurred_at=event.occurred_at,
                )
            )
