"""In-memory current product key provider implementation."""

from __future__ import annotations

import asyncio

from gateway.application.common import InternalError


class InMemoryCurrentProductKeyProvider:
    """Stores the current plaintext product key in process memory only."""

    def __init__(self, current_key: str | None = None) -> None:
        self._current_key = current_key
        self._lock = asyncio.Lock()

    async def require_current(self) -> str:
        async with self._lock:
            if self._current_key is None:
                raise InternalError("No current product key is loaded")
            return self._current_key

    async def load_current(self, current_key: str | None) -> None:
        async with self._lock:
            self._current_key = current_key
