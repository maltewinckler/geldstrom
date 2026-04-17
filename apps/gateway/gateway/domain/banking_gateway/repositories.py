"""Repository contracts for banking gateway domain."""

from __future__ import annotations

from typing import Protocol

from gateway.domain.banking_gateway.value_objects import (
    BankLeitzahl,
    FinTSInstitute,
    FinTSProductRegistration,
)


class FinTSInstituteRepository(Protocol):
    """Persistence contract for canonical institute records (read-only gateway side)."""

    async def get_by_blz(self, blz: BankLeitzahl) -> FinTSInstitute | None: ...
    async def list_all(self) -> list[FinTSInstitute]: ...


class InstituteCacheLoader(Protocol):
    """Write interface for loading the in-memory institute cache."""

    async def load(self, institutes: list[FinTSInstitute]) -> None: ...


class FinTSProductRegistrationRepository(Protocol):
    """Persistence contract for the current product registration."""

    async def get_current(self) -> FinTSProductRegistration | None: ...
