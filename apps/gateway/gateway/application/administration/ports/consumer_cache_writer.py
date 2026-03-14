"""Consumer cache write port for administration use cases."""

from __future__ import annotations

from typing import Protocol

from gateway.domain.consumer_access import ApiConsumer


class ConsumerCacheWriter(Protocol):
    """Refresh or evict one consumer from the auth read model."""

    async def reload_one(self, consumer: ApiConsumer) -> None: ...
