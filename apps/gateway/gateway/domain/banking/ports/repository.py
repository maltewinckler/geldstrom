"""BankDirectoryRepository port.

Kept close to the banking domain it serves: resolves bank codes to endpoints.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from gateway.domain.banking.value_objects.connection import (
    BankEndpoint,
    BankingProtocol,
)


@runtime_checkable
class BankDirectoryRepository(Protocol):
    """Resolves bank codes to connection endpoints per protocol."""

    async def resolve(
        self, bank_code: str, protocol: BankingProtocol
    ) -> BankEndpoint | None: ...
