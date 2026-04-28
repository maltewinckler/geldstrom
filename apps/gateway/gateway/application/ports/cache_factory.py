"""Cache sub-factory port."""

from __future__ import annotations

from typing import Protocol

from gateway.domain.banking_gateway import (
    FinTSInstituteRepository,
    OperationSessionStore,
)


class CacheFactory(Protocol):
    """Provides in-memory cache instances."""

    @property
    def institute(self) -> FinTSInstituteRepository: ...

    @property
    def session_store(self) -> OperationSessionStore: ...
