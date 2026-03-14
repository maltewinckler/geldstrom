"""In-memory canonical institute cache for gateway banking requests."""

from __future__ import annotations

import asyncio

from gateway.domain.institution_catalog import BankLeitzahl, FinTSInstitute


class InMemoryFinTSInstituteCache:
    """Stores canonical institutes keyed by BLZ in process memory."""

    def __init__(self) -> None:
        self._institutes: dict[str, FinTSInstitute] = {}
        self._lock = asyncio.Lock()

    async def get_by_blz(self, blz: BankLeitzahl) -> FinTSInstitute | None:
        async with self._lock:
            return self._institutes.get(str(blz))

    async def load(self, institutes: list[FinTSInstitute]) -> None:
        async with self._lock:
            self._institutes = {
                institute.blz.value: institute for institute in institutes
            }
