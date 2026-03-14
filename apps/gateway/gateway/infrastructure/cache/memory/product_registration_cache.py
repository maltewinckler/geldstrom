"""In-memory cache for the current encrypted product registration."""

from __future__ import annotations

import asyncio

from gateway.domain.product_registration import FinTSProductRegistration


class InMemoryProductRegistrationCache:
    """Stores the current product registration in process memory."""

    def __init__(self) -> None:
        self._current: FinTSProductRegistration | None = None
        self._lock = asyncio.Lock()

    async def get_current(self) -> FinTSProductRegistration | None:
        async with self._lock:
            return self._current

    async def set_current(
        self, registration: FinTSProductRegistration | None
    ) -> None:
        async with self._lock:
            self._current = registration
