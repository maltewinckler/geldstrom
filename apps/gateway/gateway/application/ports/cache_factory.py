"""Cache sub-factory port with merged read/write protocol types."""

from __future__ import annotations

from typing import Protocol

from gateway.application.administration.ports.consumer_cache_writer import (
    ConsumerCacheWriter,
)
from gateway.application.administration.ports.institute_cache import (
    InstituteCacheLoader,
)
from gateway.application.administration.ports.product_key_loader import (
    CurrentProductKeyLoader,
)
from gateway.application.administration.ports.product_registration_cache import (
    ProductRegistrationCachePort,
)
from gateway.application.auth.ports.consumer_cache import ConsumerCachePort
from gateway.application.banking.ports.institute_catalog import InstituteCatalogPort
from gateway.application.banking.ports.pending_operation_store import (
    PendingOperationRuntimeStore,
)
from gateway.application.product_registration.ports.current_product_key import (
    CurrentProductKeyProvider,
)


class ConsumerCache(ConsumerCachePort, ConsumerCacheWriter, Protocol): ...


class InstituteCache(InstituteCatalogPort, InstituteCacheLoader, Protocol): ...


class ProductKeyCache(CurrentProductKeyProvider, CurrentProductKeyLoader, Protocol): ...


class CacheFactory(Protocol):
    """Provides in-memory cache instances."""

    @property
    def consumer(self) -> ConsumerCache: ...

    @property
    def institute(self) -> InstituteCache: ...

    @property
    def product_key(self) -> ProductKeyCache: ...

    @property
    def product_registration(self) -> ProductRegistrationCachePort: ...

    @property
    def session_store(self) -> PendingOperationRuntimeStore: ...
