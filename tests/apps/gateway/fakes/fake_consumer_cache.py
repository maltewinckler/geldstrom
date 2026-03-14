"""In-memory fake consumer cache for application tests."""

from __future__ import annotations

from gateway.domain.consumer_access import ApiConsumer


class FakeConsumerCache:
    """Stores active consumers in memory for authentication tests."""

    def __init__(self, consumers: list[ApiConsumer] | None = None) -> None:
        self._consumers = list(consumers or [])

    async def list_active(self) -> list[ApiConsumer]:
        return list(self._consumers)

    async def load(self, consumers: list[ApiConsumer]) -> None:
        self._consumers = list(consumers)

    async def append(self, consumer: ApiConsumer) -> None:
        self._consumers.append(consumer)
