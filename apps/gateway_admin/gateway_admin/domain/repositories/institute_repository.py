"""Repository protocol for the canonical institute catalog (admin write side)."""

from __future__ import annotations

from typing import Protocol

from gateway_admin.domain.entities.institutes import FinTSInstitute
from gateway_admin.domain.value_objects.institutes import BankLeitzahl


class AdminInstituteRepository(Protocol):
    async def get_by_blz(self, blz: BankLeitzahl) -> FinTSInstitute | None: ...

    async def list_all(self) -> list[FinTSInstitute]: ...

    async def replace_catalog(self, institutes: list[FinTSInstitute]) -> None: ...
