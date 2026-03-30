"""Repository contracts for banking gateway domain."""

from __future__ import annotations

from typing import Protocol

from .value_objects import BankLeitzahl, FinTSInstitute, FinTSProductRegistration


class FinTSInstituteRepository(Protocol):
    """Persistence contract for canonical institute records (read-only gateway side)."""

    async def get_by_blz(self, blz: BankLeitzahl) -> FinTSInstitute | None:
        """Load one institute by BLZ."""

    async def list_all(self) -> list[FinTSInstitute]:
        """Load the entire canonical institute catalog."""


class InstituteCacheLoader(Protocol):
    """Write interface for loading the in-memory institute cache."""

    async def load(self, institutes: list[FinTSInstitute]) -> None:
        """Replace the cache contents with the given institute list."""


class FinTSProductRegistrationRepository(Protocol):
    """Persistence contract for the current product registration."""

    async def get_current(self) -> FinTSProductRegistration | None:
        """Load the current shared product registration, if present."""
