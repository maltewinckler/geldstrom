"""Repository contracts for the consumer access domain."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from .model import ApiConsumer


class ApiConsumerRepository(Protocol):
    """Persistence contract for API consumers."""

    async def list_all(self) -> list[ApiConsumer]:
        """Return all consumers for administrative use cases."""

    async def get_by_id(self, consumer_id: UUID) -> ApiConsumer | None:
        """Load one consumer by its identifier."""

    async def get_by_email(self, email: str) -> ApiConsumer | None:
        """Load one consumer by normalized email address."""

    async def list_all_active(self) -> list[ApiConsumer]:
        """Return all active consumers used to hydrate the auth cache."""


class ConsumerCache(Protocol):
    """In-memory consumer cache: read and write interface."""

    async def list_active(self) -> list[ApiConsumer]:
        """Return only ACTIVE consumers from the cache snapshot."""

    async def list_all(self) -> list[ApiConsumer]:
        """Return all cached consumers regardless of status (ACTIVE + DISABLED)."""

    async def load(self, consumers: list[ApiConsumer]) -> None:
        """Replace the cache contents with the given consumer list."""

    async def evict(self, consumer_id: UUID) -> None:
        """Remove a single consumer from the cache."""

    async def reload_one(self, consumer: ApiConsumer) -> None:
        """Insert or update a single consumer in the cache."""

    async def get_by_key_prefix(self, prefix: str) -> ApiConsumer | None:
        """Look up a consumer by the first 8 hex chars of the API key."""
