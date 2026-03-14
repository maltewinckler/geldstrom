"""Consumer cache read model port for authentication."""

from __future__ import annotations

from typing import Protocol

from gateway.domain.consumer_access import ApiConsumer


class ConsumerCachePort(Protocol):
    """Read model of active consumers used for API key authentication."""

    async def list_active(self) -> list[ApiConsumer]:
        """Return the active-consumer cache snapshot."""
