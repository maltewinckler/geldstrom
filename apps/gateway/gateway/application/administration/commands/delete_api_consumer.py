"""Delete API consumers administratively."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self
from uuid import UUID

from gateway.application.common import ValidationError
from gateway.domain.consumer_access import ApiConsumerRepository, ConsumerId

from ..dtos.api_consumer import ApiConsumerSummary, to_consumer_summary
from ..ports.consumer_cache_writer import ConsumerCacheWriter

if TYPE_CHECKING:
    from gateway.application.ports import ApplicationFactory


class DeleteApiConsumerCommand:
    """Mark one API consumer as deleted and clear retained key material."""

    def __init__(
        self,
        repository: ApiConsumerRepository,
        consumer_cache: ConsumerCacheWriter,
    ) -> None:
        self._repository = repository
        self._consumer_cache = consumer_cache

    @classmethod
    def from_factory(cls, factory: ApplicationFactory) -> Self:
        return cls(
            repository=factory.repos.consumer,
            consumer_cache=factory.caches.consumer,
        )

    async def __call__(self, consumer_id: str) -> ApiConsumerSummary:
        consumer = await self._repository.get_by_id(ConsumerId(UUID(consumer_id)))
        if consumer is None:
            raise ValidationError(f"No API consumer found for id {consumer_id}")

        consumer.mark_deleted()
        consumer.api_key_hash = None
        await self._repository.save(consumer)
        await self._consumer_cache.reload_one(consumer)
        return to_consumer_summary(consumer)
