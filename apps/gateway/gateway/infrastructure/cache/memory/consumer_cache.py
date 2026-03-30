"""In-memory active-consumer cache used by gateway authentication."""

from __future__ import annotations

import asyncio
from uuid import UUID

from gateway.domain.consumer_access import (
    ApiConsumer,
    ConsumerCache,
    ConsumerStatus,
)

_CACHED_STATUSES = frozenset((ConsumerStatus.ACTIVE, ConsumerStatus.DISABLED))


class InMemoryApiConsumerCache(ConsumerCache):
    """Stores ACTIVE and DISABLED consumers in process memory for authentication."""

    def __init__(self) -> None:
        self._consumers: dict[str, ApiConsumer] = {}
        self._lock = asyncio.Lock()

    async def list_active(self) -> list[ApiConsumer]:
        async with self._lock:
            return [
                c for c in self._consumers.values() if c.status is ConsumerStatus.ACTIVE
            ]

    async def list_all(self) -> list[ApiConsumer]:
        async with self._lock:
            return list(self._consumers.values())

    async def load(self, consumers: list[ApiConsumer]) -> None:
        cached = {
            str(consumer.consumer_id): consumer
            for consumer in consumers
            if consumer.status in _CACHED_STATUSES
        }
        async with self._lock:
            self._consumers = cached

    async def evict(self, consumer_id: UUID) -> None:
        async with self._lock:
            self._consumers.pop(str(consumer_id), None)

    async def reload_one(self, consumer: ApiConsumer) -> None:
        async with self._lock:
            if consumer.status in _CACHED_STATUSES:
                self._consumers[str(consumer.consumer_id)] = consumer
            else:
                self._consumers.pop(str(consumer.consumer_id), None)
