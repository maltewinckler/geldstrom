"""Create API consumers for administrative workflows."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self
from uuid import UUID

from gateway.application.common import IdProvider, ValidationError
from gateway.domain.consumer_access import (
    ApiConsumer,
    ApiConsumerRepository,
    ConsumerId,
    ConsumerStatus,
    EmailAddress,
)

from ..dtos.api_consumer import ApiConsumerKeyResult, to_consumer_summary
from ..ports.api_key_service import ApiKeyService
from ..ports.consumer_cache_writer import ConsumerCacheWriter

if TYPE_CHECKING:
    from gateway.application.ports import ApplicationFactory


class CreateApiConsumerCommand:
    """Create one active API consumer and reveal the raw key once."""

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

    async def __call__(self, email: str) -> ApiConsumerKeyResult:
        normalized_email = EmailAddress(email)
        existing = await self._repository.get_by_email(normalized_email)
        if existing is not None:
            raise ValidationError(
                f"API consumer with email {normalized_email.value} already exists"
            )

        raw_key = self._api_key_service.generate()
        consumer = ApiConsumer(
            consumer_id=ConsumerId(UUID(self._id_provider.new_operation_id())),
            email=normalized_email,
            api_key_hash=self._api_key_service.hash(raw_key),
            status=ConsumerStatus.ACTIVE,
            created_at=self._id_provider.now(),
        )
        await self._repository.save(consumer)
        await self._consumer_cache.reload_one(consumer)
        return ApiConsumerKeyResult(
            consumer=to_consumer_summary(consumer),
            raw_api_key=raw_key,
        )
