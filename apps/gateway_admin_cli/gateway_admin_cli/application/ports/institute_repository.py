"""Repository port for the canonical institute catalog (admin write side)."""

from __future__ import annotations

from typing import Protocol

from gateway_admin_cli.domain.institutes import BankLeitzahl, FinTSInstitute


class AdminInstituteRepository(Protocol):
    """Persistence contract for canonical institute records (admin operations)."""

    async def get_by_blz(self, blz: BankLeitzahl) -> FinTSInstitute | None: ...

    async def list_all(self) -> list[FinTSInstitute]: ...

    async def replace_catalog(self, institutes: list[FinTSInstitute]) -> None: ...
