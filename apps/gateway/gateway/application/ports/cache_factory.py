"""Cache sub-factory port."""

from __future__ import annotations

from typing import Protocol

from gateway.domain.banking_gateway import (
    FinTSInstituteRepository,
    OperationSessionStore,
)
from gateway.domain.consumer_access import ConsumerCache


class CacheFactory(Protocol):
    """Provides in-memory cache instances."""

    @property
    def consumer(self) -> ConsumerCache: ...

    @property
    def institute(self) -> FinTSInstituteRepository: ...

    @property
    def session_store(self) -> OperationSessionStore: ...
