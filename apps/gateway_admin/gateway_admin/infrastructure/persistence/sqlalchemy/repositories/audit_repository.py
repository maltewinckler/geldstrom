"""SQLAlchemy repository for audit events (read + write) in gateway_admin."""

from __future__ import annotations

from gateway_contracts.schema import audit_events_table
from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncEngine

from gateway_admin.domain.audit import AuditEvent, AuditEventType, AuditPage, AuditQuery


class AuditRepositorySqlAlchemy:
    """Persist and query audit events using the shared audit_events table."""

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

    async def query(self, q: AuditQuery) -> AuditPage:
        # Build WHERE predicates
        predicates = []
        if q.consumer_id is not None:
            predicates.append(audit_events_table.c.consumer_id == q.consumer_id)
        if q.event_type is not None:
            predicates.append(audit_events_table.c.event_type == q.event_type.value)
        if q.from_date is not None:
            predicates.append(audit_events_table.c.occurred_at >= q.from_date)
        if q.to_date is not None:
            predicates.append(audit_events_table.c.occurred_at <= q.to_date)

        # COUNT(*) for total matching rows
        count_stmt = select(func.count()).select_from(audit_events_table)
        if predicates:
            count_stmt = count_stmt.where(*predicates)

        # Paginated SELECT ordered by occurred_at DESC
        offset = (q.page - 1) * q.page_size
        select_stmt = (
            select(audit_events_table)
            .order_by(audit_events_table.c.occurred_at.desc())
            .limit(q.page_size)
            .offset(offset)
        )
        if predicates:
            select_stmt = select_stmt.where(*predicates)

        async with self._engine.connect() as conn:
            total: int = (await conn.execute(count_stmt)).scalar_one()
            rows = (await conn.execute(select_stmt)).mappings().all()

        events = [
            AuditEvent(
                event_id=row["event_id"],
                event_type=AuditEventType(row["event_type"]),
                consumer_id=row["consumer_id"],
                occurred_at=row["occurred_at"],
            )
            for row in rows
        ]

        return AuditPage(
            events=events,
            total=total,
            page=q.page,
            page_size=q.page_size,
        )
