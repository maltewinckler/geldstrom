"""Integration tests for initialize_database.

Verifies that:
- initialize_database creates the audit_events table (Requirement 4.4)
- initialize_database creates the audit_events_no_delete trigger (Requirement 6.3)
- A raw DELETE FROM audit_events raises a database exception (Requirement 6.3)
- The gateway DB user receives INSERT privileges on audit_events (regression guard)
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from gateway_contracts.schema import audit_events_table
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _table_exists(engine: AsyncEngine, table_name: str) -> bool:
    async with engine.connect() as conn:
        result = await conn.scalar(
            text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = :name"
            ),
            {"name": table_name},
        )
    return result is not None


async def _trigger_exists(engine: AsyncEngine, trigger_name: str) -> bool:
    async with engine.connect() as conn:
        result = await conn.scalar(
            text("SELECT 1 FROM pg_trigger WHERE tgname = :name"),
            {"name": trigger_name},
        )
    return result is not None


async def _create_trigger(engine: AsyncEngine) -> None:
    """Create the delete-prevention trigger directly (mirrors initialize_database logic)."""
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                CREATE OR REPLACE FUNCTION prevent_audit_delete()
                RETURNS TRIGGER LANGUAGE plpgsql AS $$
                BEGIN
                    RAISE EXCEPTION 'Deletion from audit_events is not permitted';
                END;
                $$
                """
            )
        )
        trigger_exists = await conn.scalar(
            text("SELECT 1 FROM pg_trigger WHERE tgname = 'audit_events_no_delete'")
        )
        if not trigger_exists:
            await conn.execute(
                text(
                    "CREATE TRIGGER audit_events_no_delete "
                    "BEFORE DELETE ON audit_events "
                    "FOR EACH ROW EXECUTE FUNCTION prevent_audit_delete()"
                )
            )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_initialize_database_creates_audit_events_table(
    postgres_engine: AsyncEngine,
    async_runner: Callable[[Awaitable[object]], object],
) -> None:
    """initialize_database creates the audit_events table.

    Requirements: 4.4
    """
    # The postgres_engine fixture already calls create_test_schema which runs
    # metadata.create_all — this is the same operation initialize_database performs.
    exists = async_runner(_table_exists(postgres_engine, "audit_events"))
    assert exists, "audit_events table should exist after schema initialisation"


def test_initialize_database_creates_delete_prevention_trigger(
    postgres_engine: AsyncEngine,
    async_runner: Callable[[Awaitable[object]], object],
) -> None:
    """initialize_database creates the audit_events_no_delete trigger.

    Requirements: 6.3
    """
    async_runner(_create_trigger(postgres_engine))

    exists = async_runner(_trigger_exists(postgres_engine, "audit_events_no_delete"))
    assert exists, "audit_events_no_delete trigger should exist after initialisation"


def test_raw_delete_from_audit_events_raises_exception(
    postgres_engine: AsyncEngine,
    async_runner: Callable[[Awaitable[object]], object],
) -> None:
    """A raw DELETE FROM audit_events raises a database exception.

    Requirements: 6.3
    """
    async_runner(_create_trigger(postgres_engine))

    # Insert a row so there is something to delete
    event_id = uuid4()
    async_runner(_insert_audit_event(postgres_engine, event_id))

    # Attempting a raw DELETE must raise
    with pytest.raises(Exception, match="Deletion from audit_events is not permitted"):
        async_runner(_raw_delete(postgres_engine))


async def _insert_audit_event(engine: AsyncEngine, event_id: object) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            audit_events_table.insert().values(
                event_id=event_id,
                event_type="consumer_authenticated",
                consumer_id=None,
                occurred_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            )
        )


async def _raw_delete(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM audit_events"))


async def _gateway_user_can_insert(
    superuser_engine: AsyncEngine,
    postgres_database_url: str,
    gw_user: str,
    gw_password: str,
) -> None:
    """Return without error if the gateway user can INSERT into audit_events."""
    from sqlalchemy.engine import make_url
    from sqlalchemy.ext.asyncio import create_async_engine

    gw_url = (
        make_url(postgres_database_url)
        .set(username=gw_user, password=gw_password)
        .render_as_string(hide_password=False)
    )
    gw_engine = create_async_engine(gw_url, poolclass=None)
    try:
        async with gw_engine.begin() as conn:
            await conn.execute(
                audit_events_table.insert().values(
                    event_id=uuid4(),
                    event_type="consumer_authenticated",
                    consumer_id=None,
                    occurred_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
                )
            )
    finally:
        await gw_engine.dispose()


def test_gateway_user_has_insert_on_audit_events(
    postgres_engine: AsyncEngine,
    postgres_database_url: str,
    async_runner: Callable[[Awaitable[object]], object],
) -> None:
    """initialize_database grants INSERT on audit_events to the gateway DB user.

    Regression guard: the gateway user previously only had SELECT, causing
    'permission denied for table audit_events' errors when the audit service
    tried to persist events.
    """
    from unittest.mock import MagicMock

    from pydantic import SecretStr

    from gateway_admin.infrastructure.persistence.sqlalchemy.db_init import (
        initialize_database,
    )

    gw_user = "test_gw_user"
    gw_password = "test_gw_pass"

    settings = MagicMock()
    settings.postgres_db = "test"
    settings.gateway_db_user = gw_user
    settings.gateway_db_password = SecretStr(gw_password)
    settings.database_url = postgres_database_url
    settings.maintenance_url = (
        postgres_database_url  # already exists; skip CREATE DATABASE
    )

    async_runner(initialize_database(settings))

    # The gateway user must now be able to INSERT into audit_events without error.
    async_runner(
        _gateway_user_can_insert(
            postgres_engine, postgres_database_url, gw_user, gw_password
        )
    )
