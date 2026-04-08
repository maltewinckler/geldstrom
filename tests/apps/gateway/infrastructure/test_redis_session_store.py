"""Tests for the Redis-backed operation session store."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

import fakeredis.aioredis

from gateway.domain.banking_gateway import (
    BankProtocol,
    OperationStatus,
    OperationType,
    PendingOperationSession,
)
from gateway.infrastructure.cache.redis import RedisOperationSessionStore


def _run(coro_fn):
    """Run an async function that receives a fresh store inside a single event loop."""

    async def _inner():
        redis = fakeredis.aioredis.FakeRedis()
        store = RedisOperationSessionStore(redis)
        return await coro_fn(store)

    return asyncio.run(_inner())


def test_redis_session_store_create_get_update_and_delete() -> None:
    async def _test(store):
        session = _session()

        await store.create(session)
        loaded = await store.get(session.operation_id)
        assert loaded == session

        updated = loaded.model_copy(
            update={"status": OperationStatus.FAILED, "failure_reason": "failed"}
        )
        await store.update(updated)
        assert await store.get(session.operation_id) == updated

        await store.delete(session.operation_id)
        assert await store.get(session.operation_id) is None

    _run(_test)


def test_redis_session_store_get_returns_none_for_missing() -> None:
    async def _test(store):
        assert await store.get("nonexistent") is None

    _run(_test)


def test_redis_session_store_expires_stale_terminal_sessions() -> None:
    async def _test(store):
        stale = _session(
            expires_at=datetime(2026, 3, 7, 12, 5, tzinfo=UTC),
            status=OperationStatus.EXPIRED,
        )
        fresh = _session(
            operation_id="op-2",
            expires_at=datetime(2026, 3, 7, 12, 30, tzinfo=UTC),
        )
        await store.create(stale)
        await store.create(fresh)

        expired = await store.expire_stale(datetime(2026, 3, 7, 12, 10, tzinfo=UTC))

        assert expired == 1
        assert await store.get(stale.operation_id) is None
        assert await store.get(fresh.operation_id) == fresh

    _run(_test)


def test_redis_session_store_does_not_expire_pending() -> None:
    async def _test(store):
        pending = _session(expires_at=datetime(2026, 3, 7, 12, 5, tzinfo=UTC))
        await store.create(pending)

        expired = await store.expire_stale(datetime(2026, 3, 7, 12, 10, tzinfo=UTC))

        assert expired == 0
        assert await store.get(pending.operation_id) is not None

    _run(_test)


def test_redis_session_store_lists_all_sessions() -> None:
    async def _test(store):
        first = _session()
        second = _session(operation_id="op-2")
        await store.create(first)
        await store.create(second)

        loaded = await store.list_all()

        assert sorted(loaded, key=lambda s: s.operation_id) == sorted(
            [first, second], key=lambda s: s.operation_id
        )

    _run(_test)


def test_redis_session_store_preserves_completed_payload() -> None:
    async def _test(store):
        session = PendingOperationSession(
            operation_id="op-complete",
            consumer_id=UUID("12345678-1234-5678-1234-567812345678"),
            protocol=BankProtocol.FINTS,
            operation_type=OperationType.TRANSACTIONS,
            session_state=None,
            status=OperationStatus.COMPLETED,
            created_at=datetime(2026, 3, 7, 12, 0, tzinfo=UTC),
            expires_at=datetime(2026, 3, 7, 12, 15, tzinfo=UTC),
            result_payload={"transactions": [{"id": "txn-1", "amount": "12.34"}]},
        )
        await store.create(session)

        loaded = await store.get("op-complete")
        assert loaded is not None
        assert loaded.result_payload == session.result_payload
        assert loaded.status is OperationStatus.COMPLETED

    _run(_test)


def test_redis_session_store_preserves_session_state_bytes() -> None:
    async def _test(store):
        session = _session()
        await store.create(session)

        loaded = await store.get(session.operation_id)
        assert loaded is not None
        assert loaded.session_state == b"session-state"

    _run(_test)


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
        operation_type=OperationType.ACCOUNTS,
        session_state=b"session-state",
        status=status,
        created_at=datetime(2026, 3, 7, 12, 0, tzinfo=UTC),
        expires_at=expires_at,
    )
