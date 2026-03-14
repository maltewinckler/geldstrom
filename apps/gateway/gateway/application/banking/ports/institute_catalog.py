"""Read-only institute catalog port for banking use cases."""

from __future__ import annotations

from typing import Protocol

from gateway.domain.institution_catalog import BankLeitzahl, FinTSInstitute


class InstituteCatalogPort(Protocol):
    """Read-only catalog lookup used by banking application services."""

    async def get_by_blz(self, blz: BankLeitzahl) -> FinTSInstitute | None:
        """Return the canonical institute for the provided BLZ."""
