"""Property test for audit event round-trip (Property 4).

# Feature: audit-log, Property 4: audit event round-trip

Validates: Requirements 4.1, 4.2, 6.2
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from hypothesis import given, settings
from hypothesis import strategies as st
from sqlalchemy import Column, DateTime, MetaData, String, Table, Uuid, select
from sqlalchemy.ext.asyncio import create_async_engine

from gateway.domain.audit import AuditEvent, AuditEventType
from gateway.infrastructure.persistence.sqlalchemy import AuditRepositorySqlAlchemy

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_event_type_strategy = st.sampled_from(list(AuditEventType))

_uuid_strategy = st.uuids()

_utc_datetime_strategy = st.datetimes(
    min_value=datetime(2000, 1, 1),
    max_value=datetime(2100, 1, 1),
    timezones=st.just(UTC),
)

_audit_event_strategy = st.builds(
    AuditEvent,
    event_id=_uuid_strategy,
    event_type=_event_type_strategy,
    consumer_id=st.one_of(st.none(), _uuid_strategy),
    occurred_at=_utc_datetime_strategy,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# SQLite-compatible table definition (Uuid columns work via SQLAlchemy's
# native_uuid=False fallback — SQLAlchemy stores UUIDs as strings in SQLite)
_sqlite_metadata = MetaData()
_sqlite_audit_events_table = Table(
    "audit_events",
    _sqlite_metadata,
    Column("event_id", Uuid(as_uuid=True, native_uuid=False), primary_key=True),
    Column("event_type", String(64), nullable=False),
    Column("consumer_id", Uuid(as_uuid=True, native_uuid=False), nullable=True),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
)


async def _round_trip(event: AuditEvent) -> AuditEvent:
    """Write an AuditEvent via AuditRepositorySqlAlchemy and read it back."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    try:
        # Create schema
        async with engine.begin() as conn:
            await conn.run_sync(_sqlite_metadata.create_all)

        # Write via the repository under test
        repo = AuditRepositorySqlAlchemy(engine)
        await repo.append(event)

        # Read back directly via SELECT
        async with engine.connect() as conn:
            row = await conn.execute(
                select(_sqlite_audit_events_table).where(
                    _sqlite_audit_events_table.c.event_id == event.event_id
                )
            )
            r = row.fetchone()

        assert r is not None, "Row must exist after append"

        return AuditEvent(
            event_id=r.event_id
            if isinstance(r.event_id, UUID)
            else UUID(str(r.event_id)),
            event_type=AuditEventType(r.event_type),
            consumer_id=(
                r.consumer_id
                if r.consumer_id is None or isinstance(r.consumer_id, UUID)
                else UUID(str(r.consumer_id))
            ),
            occurred_at=r.occurred_at.replace(tzinfo=UTC)
            if r.occurred_at.tzinfo is None
            else r.occurred_at,
        )
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# Property 4: Audit event round-trip
# Validates: Requirements 4.1, 4.2, 6.2
# ---------------------------------------------------------------------------


@given(event=_audit_event_strategy)
@settings(max_examples=100)
def test_property_4_audit_event_round_trip(event: AuditEvent) -> None:
    """Property 4: For any valid AuditEvent, writing via AuditRepositorySqlAlchemy and
    reading back produces a record identical to the one written.

    Validates: Requirements 4.1, 4.2, 6.2
    """
    # Feature: audit-log, Property 4: audit event round-trip
    retrieved = asyncio.run(_round_trip(event))

    assert retrieved.event_id == event.event_id
    assert retrieved.event_type == event.event_type
    assert retrieved.consumer_id == event.consumer_id
    # Compare timestamps as UTC — SQLite may strip tzinfo on read-back
    assert retrieved.occurred_at.replace(tzinfo=UTC) == event.occurred_at.replace(
        tzinfo=UTC
    )
