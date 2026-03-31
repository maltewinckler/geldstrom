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


def _consumer_key_prefix(consumer_id: UUID) -> str:
    """Return the first 8 hex chars of the consumer UUID (matches API key prefix)."""
    return consumer_id.hex[:8]


class InMemoryApiConsumerCache(ConsumerCache):
    """Stores ACTIVE and DISABLED consumers in process memory for authentication."""

    def __init__(self) -> None:
        self._consumers: dict[str, ApiConsumer] = {}
        self._prefix_index: dict[str, str] = {}  # key prefix -> consumer str id
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
        cached: dict[str, ApiConsumer] = {}
        prefix_idx: dict[str, str] = {}
        for consumer in consumers:
            if consumer.status in _CACHED_STATUSES:
                cid = str(consumer.consumer_id)
                cached[cid] = consumer
                prefix_idx[_consumer_key_prefix(consumer.consumer_id)] = cid
        async with self._lock:
            self._consumers = cached
            self._prefix_index = prefix_idx

    async def evict(self, consumer_id: UUID) -> None:
        cid = str(consumer_id)
        prefix = _consumer_key_prefix(consumer_id)
        async with self._lock:
            self._consumers.pop(cid, None)
            if self._prefix_index.get(prefix) == cid:
                self._prefix_index.pop(prefix, None)

    async def reload_one(self, consumer: ApiConsumer) -> None:
        cid = str(consumer.consumer_id)
        prefix = _consumer_key_prefix(consumer.consumer_id)
        async with self._lock:
            if consumer.status in _CACHED_STATUSES:
                self._consumers[cid] = consumer
                self._prefix_index[prefix] = cid
            else:
                self._consumers.pop(cid, None)
                if self._prefix_index.get(prefix) == cid:
                    self._prefix_index.pop(prefix, None)

    async def get_by_key_prefix(self, prefix: str) -> ApiConsumer | None:
        """Look up a consumer by the first 8 hex chars of the API key."""
        async with self._lock:
            cid = self._prefix_index.get(prefix)
            if cid is None:
                return None
            return self._consumers.get(cid)
