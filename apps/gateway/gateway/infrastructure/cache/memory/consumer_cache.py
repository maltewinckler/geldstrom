"""In-memory active-consumer cache used by gateway authentication."""

from __future__ import annotations

import asyncio

from gateway.domain.consumer_access import ApiConsumer, ConsumerId, ConsumerStatus


class InMemoryApiConsumerCache:
    """Stores the active-consumer read model entirely in process memory."""

    def __init__(self) -> None:
        self._consumers: dict[str, ApiConsumer] = {}
        self._lock = asyncio.Lock()

    async def list_active(self) -> list[ApiConsumer]:
        async with self._lock:
            return list(self._consumers.values())

    async def load(self, consumers: list[ApiConsumer]) -> None:
        active_consumers = {
            str(consumer.consumer_id): consumer
            for consumer in consumers
            if consumer.status is ConsumerStatus.ACTIVE
        }
        async with self._lock:
            self._consumers = active_consumers

    async def evict(self, consumer_id: ConsumerId) -> None:
        async with self._lock:
            self._consumers.pop(str(consumer_id), None)

    async def reload_one(self, consumer: ApiConsumer) -> None:
        async with self._lock:
            if consumer.status is ConsumerStatus.ACTIVE:
                self._consumers[str(consumer.consumer_id)] = consumer
            else:
                self._consumers.pop(str(consumer.consumer_id), None)
