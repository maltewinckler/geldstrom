"""In-memory fake institute cache for application tests."""

from __future__ import annotations

from gateway.domain.banking_gateway import BankLeitzahl, FinTSInstitute


class FakeInstituteCache:
    """Stores canonical institutes indexed by BLZ."""

    def __init__(self, institutes: list[FinTSInstitute] | None = None) -> None:
        self._institutes: dict[str, FinTSInstitute] = {}
        for institute in institutes or []:
            self._institutes[str(institute.blz)] = institute

    async def get_by_blz(self, blz: BankLeitzahl) -> FinTSInstitute | None:
        return self._institutes.get(str(blz))

    async def list_all(self) -> list[FinTSInstitute]:
        return list(self._institutes.values())

    async def load(self, institutes: list[FinTSInstitute]) -> None:
        self._institutes = {str(institute.blz): institute for institute in institutes}
