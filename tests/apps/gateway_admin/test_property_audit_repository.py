"""Property tests for gateway_admin PostgresAuditRepository (Properties 5, 6, 7).

Validates: Requirements 5.1, 5.2, 5.3, 5.4
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from hypothesis import given, settings
from hypothesis import strategies as st
from sqlalchemy import Column, DateTime, MetaData, String, Table, Uuid
from sqlalchemy.ext.asyncio import create_async_engine

from gateway_admin.domain.audit import AuditEvent, AuditEventType, AuditPage, AuditQuery
from gateway_admin.infrastructure.persistence.sqlalchemy.repositories.audit_repository import (
    AuditRepositorySqlAlchemy,
)

# ---------------------------------------------------------------------------
# SQLite-compatible table (Uuid stored as string)
# ---------------------------------------------------------------------------

_sqlite_metadata = MetaData()
_sqlite_audit_events_table = Table(
    "audit_events",
    _sqlite_metadata,
    Column("event_id", Uuid(as_uuid=True, native_uuid=False), primary_key=True),
    Column("event_type", String(64), nullable=False),
    Column("consumer_id", Uuid(as_uuid=True, native_uuid=False), nullable=True),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
)

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


@st.composite
def _audit_event_strategy(draw: st.DrawFn) -> AuditEvent:
    return AuditEvent(
        event_id=draw(_uuid_strategy),
        event_type=draw(_event_type_strategy),
        consumer_id=draw(st.one_of(st.none(), _uuid_strategy)),
        occurred_at=draw(_utc_datetime_strategy),
    )


@st.composite
def _distinct_timestamp_events(draw: st.DrawFn) -> list[AuditEvent]:
    """Generate a list of AuditEvents with distinct timestamps."""
    n = draw(st.integers(min_value=1, max_value=20))
    timestamps = draw(
        st.lists(
            _utc_datetime_strategy,
            min_size=n,
            max_size=n,
            unique=True,
        )
    )
    events = []
    for ts in timestamps:
        events.append(
            AuditEvent(
                event_id=draw(_uuid_strategy),
                event_type=draw(_event_type_strategy),
                consumer_id=draw(st.one_of(st.none(), _uuid_strategy)),
                occurred_at=ts,
            )
        )
    return events


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _setup_repo(
    events: list[AuditEvent],
) -> tuple[AuditRepositorySqlAlchemy, object]:
    """Create an in-memory SQLite engine, create schema, insert events, return repo."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(_sqlite_metadata.create_all)

    # Use the repo's append to insert events (tests the write path too)
    repo = AuditRepositorySqlAlchemy(engine)
    for event in events:
        await repo.append(event)

    return repo, engine


async def _query_and_dispose(
    events: list[AuditEvent], q: AuditQuery
) -> tuple[AuditPage, list[AuditEvent]]:
    repo, engine = await _setup_repo(events)
    try:
        page = await repo.query(q)
    finally:
        await engine.dispose()
    return page, events


# ---------------------------------------------------------------------------
# Property 5: Query results ordered descending and pagination respected
# Validates: Requirements 5.1
# ---------------------------------------------------------------------------


@given(
    events=_distinct_timestamp_events(),
    page=st.integers(min_value=1, max_value=5),
    page_size=st.integers(min_value=1, max_value=10),
)
@settings(max_examples=100)
def test_property_5_query_ordering_and_pagination(
    events: list[AuditEvent],
    page: int,
    page_size: int,
) -> None:
    """Property 5: For any set of events and any valid page/page_size, returned
    events are ordered by occurred_at descending, len <= page_size, and total
    equals the count of all inserted events.

    # Feature: audit-log, Property 5: query results ordered descending and pagination respected
    Validates: Requirements 5.1
    """
    q = AuditQuery(page=page, page_size=page_size)
    result, _ = asyncio.run(_query_and_dispose(events, q))

    # Total must equal the number of inserted events
    assert result.total == len(events)

    # Number of returned events must not exceed page_size
    assert len(result.events) <= page_size

    # Events must be ordered by occurred_at descending
    timestamps = [e.occurred_at for e in result.events]
    assert timestamps == sorted(timestamps, reverse=True)


# ---------------------------------------------------------------------------
# Property 6: Filter correctness for consumer_id and event_type
# Validates: Requirements 5.2, 5.3
# ---------------------------------------------------------------------------


@given(
    events=st.lists(_audit_event_strategy(), min_size=1, max_size=20),
    filter_consumer_id=st.one_of(st.none(), _uuid_strategy),
    filter_event_type=st.one_of(st.none(), _event_type_strategy),
)
@settings(max_examples=100)
def test_property_6_filter_correctness(
    events: list[AuditEvent],
    filter_consumer_id: UUID | None,
    filter_event_type: AuditEventType | None,
) -> None:
    """Property 6: For any combination of consumer_id and event_type filters,
    every returned event satisfies all provided predicates.

    # Feature: audit-log, Property 6: filter correctness for consumer_id and event_type
    Validates: Requirements 5.2, 5.3
    """
    q = AuditQuery(
        consumer_id=filter_consumer_id,
        event_type=filter_event_type,
        page_size=200,
    )
    result, _ = asyncio.run(_query_and_dispose(events, q))

    for event in result.events:
        if filter_consumer_id is not None:
            assert event.consumer_id == filter_consumer_id
        if filter_event_type is not None:
            assert event.event_type == filter_event_type


# ---------------------------------------------------------------------------
# Property 7: Date range filter returns only events within range
# Validates: Requirements 5.4
# ---------------------------------------------------------------------------


@given(
    events=st.lists(_audit_event_strategy(), min_size=1, max_size=20),
    date_range=st.one_of(
        # Both bounds
        st.tuples(_utc_datetime_strategy, _utc_datetime_strategy).map(
            lambda t: (min(t), max(t))
        ),
        # Only from_date
        st.tuples(_utc_datetime_strategy, st.none()),
        # Only to_date
        st.tuples(st.none(), _utc_datetime_strategy),
    ),
)
@settings(max_examples=100)
def test_property_7_date_range_filter(
    events: list[AuditEvent],
    date_range: tuple[datetime | None, datetime | None],
) -> None:
    """Property 7: For any from_date/to_date range, every returned event has
    occurred_at within [from_date, to_date] inclusive.

    # Feature: audit-log, Property 7: date range filter returns only events within range
    Validates: Requirements 5.4
    """
    from_date, to_date = date_range
    q = AuditQuery(from_date=from_date, to_date=to_date, page_size=200)
    result, _ = asyncio.run(_query_and_dispose(events, q))

    for event in result.events:
        ts = event.occurred_at.replace(tzinfo=UTC)
        if from_date is not None:
            assert ts >= from_date.replace(tzinfo=UTC)
        if to_date is not None:
            assert ts <= to_date.replace(tzinfo=UTC)
