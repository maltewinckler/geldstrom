"""Institute cache hydration port."""

from __future__ import annotations

from typing import Protocol

from gateway.domain.institution_catalog import FinTSInstitute


class InstituteCacheLoader(Protocol):
    """Hydrates the in-memory institute read model."""

    async def load(self, institutes: list[FinTSInstitute]) -> None: ...
