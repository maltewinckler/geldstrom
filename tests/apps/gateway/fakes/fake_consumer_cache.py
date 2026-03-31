"""In-memory fake consumer cache for application tests."""

from __future__ import annotations

from uuid import UUID

from gateway.domain.consumer_access import ApiConsumer, ConsumerStatus


class FakeConsumerCache:
    """Stores ACTIVE and DISABLED consumers in memory for authentication tests."""

    def __init__(self, consumers: list[ApiConsumer] | None = None) -> None:
        self._consumers = list(consumers or [])

    async def list_active(self) -> list[ApiConsumer]:
        return [c for c in self._consumers if c.status is ConsumerStatus.ACTIVE]

    async def list_all(self) -> list[ApiConsumer]:
        return list(self._consumers)

    async def load(self, consumers: list[ApiConsumer]) -> None:
        self._consumers = list(consumers)

    async def append(self, consumer: ApiConsumer) -> None:
        self._consumers.append(consumer)

    async def evict(self, consumer_id: UUID) -> None:
        self._consumers = [
            c for c in self._consumers if c.consumer_id != consumer_id
        ]

    async def reload_one(self, consumer: ApiConsumer) -> None:
        self._consumers = [
            c for c in self._consumers if c.consumer_id != consumer.consumer_id
        ]
        self._consumers.append(consumer)

    async def get_by_key_prefix(self, prefix: str) -> ApiConsumer | None:
        for consumer in self._consumers:
            if consumer.consumer_id.hex[:8] == prefix:
                return consumer
        return None
