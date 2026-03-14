"""Repository contracts for the consumer access domain."""

from __future__ import annotations

from typing import Protocol

from .model import ApiConsumer
from .value_objects import ConsumerId, EmailAddress


class ApiConsumerRepository(Protocol):
    """Persistence contract for API consumers."""

    async def list_all(self) -> list[ApiConsumer]:
        """Return all consumers for administrative use cases."""

    async def get_by_id(self, consumer_id: ConsumerId) -> ApiConsumer | None:
        """Load one consumer by its identifier."""

    async def get_by_email(self, email: EmailAddress) -> ApiConsumer | None:
        """Load one consumer by normalized email address."""

    async def list_all_active(self) -> list[ApiConsumer]:
        """Return all active consumers used to hydrate the auth cache."""

    async def save(self, consumer: ApiConsumer) -> None:
        """Persist one consumer aggregate."""
