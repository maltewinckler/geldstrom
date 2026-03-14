"""Rotate API keys for existing consumers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self
from uuid import UUID

from gateway.application.common import IdProvider, ValidationError
from gateway.domain.consumer_access import (
    ApiConsumerRepository,
    ConsumerId,
    ConsumerStatus,
)

from ..dtos.api_consumer import ApiConsumerKeyResult, to_consumer_summary
from ..ports.api_key_service import ApiKeyService
from ..ports.consumer_cache_writer import ConsumerCacheWriter

if TYPE_CHECKING:
    from gateway.application.ports import ApplicationFactory


class RotateApiConsumerKeyCommand:
    """Replace one consumer's API key hash and reveal the new raw key once."""

    def __init__(
        self,
        repository: ApiConsumerRepository,
        consumer_cache: ConsumerCacheWriter,
        api_key_service: ApiKeyService,
        id_provider: IdProvider,
    ) -> None:
        self._repository = repository
        self._consumer_cache = consumer_cache
        self._api_key_service = api_key_service
        self._id_provider = id_provider

    @classmethod
    def from_factory(cls, factory: ApplicationFactory) -> Self:
        return cls(
            repository=factory.repos.consumer,
            consumer_cache=factory.caches.consumer,
            api_key_service=factory.api_key_service,
            id_provider=factory.id_provider,
        )

    async def __call__(self, consumer_id: str) -> ApiConsumerKeyResult:
        consumer = await self._repository.get_by_id(ConsumerId(UUID(consumer_id)))
        if consumer is None:
            raise ValidationError(f"No API consumer found for id {consumer_id}")
        if consumer.status is ConsumerStatus.DELETED:
            raise ValidationError("Deleted API consumers cannot rotate keys")

        raw_key = self._api_key_service.generate()
        consumer.api_key_hash = self._api_key_service.hash(raw_key)
        consumer.rotated_at = self._id_provider.now()
        await self._repository.save(consumer)
        await self._consumer_cache.reload_one(consumer)
        return ApiConsumerKeyResult(
            consumer=to_consumer_summary(consumer),
            raw_api_key=raw_key,
        )
