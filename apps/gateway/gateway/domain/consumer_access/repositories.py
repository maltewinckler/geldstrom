"""Repository contracts for the consumer access domain."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from gateway.domain.consumer_access.model import ApiConsumer


class ApiConsumerRepository(Protocol):
    """Persistence contract for API consumers."""

    async def list_all(self) -> list[ApiConsumer]: ...
    async def get_by_id(self, consumer_id: UUID) -> ApiConsumer | None: ...
    async def get_by_email(self, email: str) -> ApiConsumer | None: ...
    async def list_all_active(self) -> list[ApiConsumer]: ...
    async def get_by_key_prefix(self, prefix: str) -> ApiConsumer | None: ...
