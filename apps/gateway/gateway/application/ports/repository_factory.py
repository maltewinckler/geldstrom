"""Repository sub-factory port."""

from __future__ import annotations

from typing import Protocol

from gateway.domain.consumer_access import ApiConsumerRepository
from gateway.domain.institution_catalog import FinTSInstituteRepository
from gateway.domain.product_registration import FinTSProductRegistrationRepository


class RepositoryFactory(Protocol):
    """Provides database-backed repository instances."""

    @property
    def consumer(self) -> ApiConsumerRepository: ...

    @property
    def institute(self) -> FinTSInstituteRepository: ...

    @property
    def product_registration(self) -> FinTSProductRegistrationRepository: ...
