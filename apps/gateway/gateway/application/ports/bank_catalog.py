"""Application port for bulk bank catalog access."""

from __future__ import annotations

from typing import Protocol

from gateway.domain.banking_gateway import FinTSInstitute


class BankCatalogPort(Protocol):
    """Narrow read port for retrieving the full bank catalog.

    Kept separate from BankMetadataPort (ISP): single-bank lookup and
    full-catalog listing are distinct capabilities with different consumers.
    """

    async def list_all(self) -> list[FinTSInstitute]: ...
