"""Authenticate gateway consumers from the active in-memory cache."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self
from uuid import UUID

from gateway.application.common import ForbiddenError, UnauthorizedError
from gateway.domain.consumer_access import (
    ApiKeyVerifier,
    ConsumerCache,
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
        prefix, _, secret = presented_key.partition(".")
        if not secret:
            raise UnauthorizedError("Invalid API key")

        consumer = await self._consumer_cache.get_by_key_prefix(prefix)
        if consumer is None:
            raise UnauthorizedError("Invalid API key")

        if consumer.is_disabled():
            raise ForbiddenError("API consumer is disabled")

        # consumer.api_key_hash is non-None here: the ACTIVE invariant on
        # ApiConsumer guarantees it (enforced by _check_active_has_hash).
        # Cache only holds ACTIVE and DISABLED, so not-disabled implies active.
        if not self._api_key_verifier.verify(presented_key, consumer.api_key_hash):  # type: ignore[arg-type]
            raise UnauthorizedError("Invalid API key")

        return consumer.consumer_id
