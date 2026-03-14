"""Tests for the in-memory API consumer cache."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from gateway.domain.consumer_access import (
    ApiConsumer,
    ApiKeyHash,
    ConsumerId,
    ConsumerStatus,
    EmailAddress,
)
from gateway.infrastructure.cache.memory import InMemoryApiConsumerCache


def test_consumer_cache_loads_only_active_consumers() -> None:
    cache = InMemoryApiConsumerCache()

    asyncio.run(cache.load([_consumer("active@example.com"), _disabled_consumer()]))

    loaded = asyncio.run(cache.list_active())

    assert loaded == [_consumer("active@example.com")]


def test_consumer_cache_evicts_by_id() -> None:
    cache = InMemoryApiConsumerCache()
    consumer = _consumer("active@example.com")
    asyncio.run(cache.load([consumer]))

    asyncio.run(cache.evict(consumer.consumer_id))

    assert asyncio.run(cache.list_active()) == []


def test_consumer_cache_reloads_one_consumer() -> None:
    cache = InMemoryApiConsumerCache()
    original = _consumer("active@example.com")
    updated = _consumer("updated@example.com")
    asyncio.run(cache.load([original]))

    asyncio.run(cache.reload_one(updated))

    assert asyncio.run(cache.list_active()) == [updated]


def test_consumer_cache_removes_non_active_reload() -> None:
    cache = InMemoryApiConsumerCache()
    original = _consumer("active@example.com")
    disabled = _disabled_consumer(consumer_id=original.consumer_id)
    asyncio.run(cache.load([original]))

    asyncio.run(cache.reload_one(disabled))

    assert asyncio.run(cache.list_active()) == []


def _consumer(email: str, *, consumer_id: ConsumerId | None = None) -> ApiConsumer:
    return ApiConsumer(
        consumer_id=consumer_id
        or ConsumerId(UUID("12345678-1234-5678-1234-567812345678")),
        email=EmailAddress(email),
        api_key_hash=ApiKeyHash("hash-1"),
        status=ConsumerStatus.ACTIVE,
        created_at=datetime(2026, 3, 7, 12, 0, tzinfo=UTC),
    )


def _disabled_consumer(
    *, consumer_id: ConsumerId | None = None
) -> ApiConsumer:
    return ApiConsumer(
        consumer_id=consumer_id
        or ConsumerId(UUID("87654321-4321-8765-4321-876543218765")),
        email=EmailAddress("disabled@example.com"),
        api_key_hash=None,
        status=ConsumerStatus.DISABLED,
        created_at=datetime(2026, 3, 7, 12, 0, tzinfo=UTC),
    )
