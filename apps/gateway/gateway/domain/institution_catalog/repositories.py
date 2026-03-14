"""Repository contracts for the institution catalog domain."""

from __future__ import annotations

from typing import Protocol

from .model import FinTSInstitute
from .value_objects import BankLeitzahl


class FinTSInstituteRepository(Protocol):
    """Persistence contract for canonical institute records."""

    async def get_by_blz(self, blz: BankLeitzahl) -> FinTSInstitute | None:
        """Load one institute by BLZ."""

    async def list_all(self) -> list[FinTSInstitute]:
        """Load the entire canonical institute catalog."""

    async def replace_catalog(self, institutes: list[FinTSInstitute]) -> None:
        """Replace the canonical catalog snapshot."""
