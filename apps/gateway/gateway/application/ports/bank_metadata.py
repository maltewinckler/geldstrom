"""Application port for bank metadata lookup."""

from __future__ import annotations

from typing import Protocol

from gateway.domain.banking_gateway import BankLeitzahl, FinTSInstitute


class BankMetadataPort(Protocol):
    """Narrow read port for resolving canonical bank metadata by BLZ.

    The application layer owns this interface.  Infrastructure provides
    a concrete implementation — the application never names it.
    """

    async def get_by_blz(self, blz: BankLeitzahl) -> FinTSInstitute | None: ...
