"""Tests for the in-memory operation session store."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID

import pytest

from gateway.application.common import InternalError
from gateway.domain.banking_gateway import (
    BankProtocol,
    OperationStatus,
    PendingOperationSession,
)
from gateway.infrastructure.cache.memory import InMemoryOperationSessionStore


def test_operation_session_store_create_get_update_and_delete() -> None:
    store = InMemoryOperationSessionStore()
    session = _session()

    asyncio.run(store.create(session))
    loaded = asyncio.run(store.get(session.operation_id))
    updated = replace(loaded, status=OperationStatus.FAILED, failure_reason="failed")
    asyncio.run(store.update(updated))

    assert asyncio.run(store.get(session.operation_id)) == updated

    asyncio.run(store.delete(session.operation_id))

    assert asyncio.run(store.get(session.operation_id)) is None


def test_operation_session_store_expires_stale_sessions() -> None:
    store = InMemoryOperationSessionStore()
    # EXPIRED terminal session — should be purged
    stale_session = _session(
        expires_at=datetime(2026, 3, 7, 12, 5, tzinfo=UTC),
        status=OperationStatus.EXPIRED,
    )
    # PENDING session with a future TTL — should not be touched
    fresh_session = _session(
        operation_id="op-2",
        expires_at=datetime(2026, 3, 7, 12, 30, tzinfo=UTC),
    )
    asyncio.run(store.create(stale_session))
    asyncio.run(store.create(fresh_session))

    expired_count = asyncio.run(
        store.expire_stale(datetime(2026, 3, 7, 12, 10, tzinfo=UTC))
    )

    assert expired_count == 1
    assert asyncio.run(store.get(stale_session.operation_id)) is None
    assert asyncio.run(store.get(fresh_session.operation_id)) == fresh_session


def test_operation_session_store_does_not_expire_pending_sessions() -> None:
    store = InMemoryOperationSessionStore()
    stale_pending = _session(expires_at=datetime(2026, 3, 7, 12, 5, tzinfo=UTC))
    asyncio.run(store.create(stale_pending))

    expired_count = asyncio.run(
        store.expire_stale(datetime(2026, 3, 7, 12, 10, tzinfo=UTC))
    )

    assert expired_count == 0
    assert asyncio.run(store.get(stale_pending.operation_id)) is not None


def test_operation_session_store_lists_all_sessions() -> None:
    store = InMemoryOperationSessionStore()
    first = _session()
    second = _session(operation_id="op-2")
    asyncio.run(store.create(first))
    asyncio.run(store.create(second))

    loaded = asyncio.run(store.list_all())

    assert loaded == [first, second]


def test_operation_session_store_enforces_max_capacity() -> None:
    store = InMemoryOperationSessionStore(max_sessions=1)
    asyncio.run(store.create(_session()))

    with pytest.raises(InternalError):
        asyncio.run(store.create(_session(operation_id="op-2")))


def _session(
    *,
    operation_id: str = "op-1",
    expires_at: datetime = datetime(2026, 3, 7, 12, 15, tzinfo=UTC),
    status: OperationStatus = OperationStatus.PENDING_CONFIRMATION,
) -> PendingOperationSession:
    return PendingOperationSession(
        operation_id=operation_id,
        consumer_id=UUID("12345678-1234-5678-1234-567812345678"),
        protocol=BankProtocol.FINTS,
        operation_type="accounts",
        session_state=b"session-state",
        status=status,
        created_at=datetime(2026, 3, 7, 12, 0, tzinfo=UTC),
        expires_at=expires_at,
    )
