"""Authenticate gateway consumers from the active in-memory cache."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self
from uuid import UUID

from gateway.application.common import ForbiddenError, UnauthorizedError
from gateway.domain.consumer_access import (
    ApiKeyVerifier,
    ConsumerCache,
    ConsumerStatus,
)

if TYPE_CHECKING:
    from gateway.application.ports import ApplicationFactory


class AuthenticateConsumerQuery:
    """Authenticate a presented API key against cached consumer hashes."""

    def __init__(
        self,
        consumer_cache: ConsumerCache,
        api_key_verifier: ApiKeyVerifier,
    ) -> None:
        self._consumer_cache = consumer_cache
        self._api_key_verifier = api_key_verifier

    @classmethod
    def from_factory(cls, factory: ApplicationFactory) -> Self:
        return cls(factory.caches.consumer, factory.api_key_verifier)

    async def __call__(self, presented_key: str) -> UUID:
        consumers = await self._consumer_cache.list_all()
        for consumer in consumers:
            if consumer.api_key_hash is None:
                continue
            if not self._api_key_verifier.verify(presented_key, consumer.api_key_hash):
                continue
            if consumer.status is ConsumerStatus.DISABLED:
                raise ForbiddenError("API consumer is disabled")
            if consumer.status is not ConsumerStatus.ACTIVE:
                break
            return consumer.consumer_id
        raise UnauthorizedError("Invalid API key")
