"""In-memory fake consumer repository for application tests."""

from __future__ import annotations

from uuid import UUID

from gateway.domain.consumer_access import ApiConsumer, ConsumerStatus


class FakeConsumerRepository:
    """In-memory ApiConsumerRepository fake for unit tests."""

    def __init__(self, consumers: list[ApiConsumer] | None = None) -> None:
        self._consumers = list(consumers or [])

    async def list_all(self) -> list[ApiConsumer]:
        return list(self._consumers)

    async def get_by_id(self, consumer_id: UUID) -> ApiConsumer | None:
        for c in self._consumers:
            if c.consumer_id == consumer_id:
                return c
        return None

    async def get_by_email(self, email: str) -> ApiConsumer | None:
        for c in self._consumers:
            if c.email == email:
                return c
        return None

    async def list_all_active(self) -> list[ApiConsumer]:
        return [c for c in self._consumers if c.status is ConsumerStatus.ACTIVE]

    async def get_by_key_prefix(self, prefix: str) -> ApiConsumer | None:
        for consumer in self._consumers:
            if consumer.consumer_id.hex[:8] == prefix:
                if consumer.status in (ConsumerStatus.ACTIVE, ConsumerStatus.DISABLED):
                    return consumer
        return None
