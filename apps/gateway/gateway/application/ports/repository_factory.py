"""Repository sub-factory port."""

from __future__ import annotations

from typing import Protocol

from gateway.domain.banking_gateway import (
    FinTSInstituteRepository,
    FinTSProductRegistrationRepository,
)
from gateway.domain.consumer_access import ApiConsumerRepository


class RepositoryFactory(Protocol):
    """Provides database-backed repository instances."""

    @property
    def consumer(self) -> ApiConsumerRepository: ...

    @property
    def institute(self) -> FinTSInstituteRepository: ...

    @property
    def product_registration(self) -> FinTSProductRegistrationRepository: ...
