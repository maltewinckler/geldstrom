"""Top-level AdminFactory protocol."""

from __future__ import annotations

from typing import Protocol

from .institute_repository import AdminInstituteRepository
from .product_repository import ProductRegistrationRepository
from .services import (
    AdminApiKeyService,
    IdProvider,
    InstituteCacheLoader,
    InstituteCsvReaderPort,
    ProductRegistrationNotifier,
    UserCacheWriter,
)
from .user_repository import UserRepository


class AdminRepositoryFactory(Protocol):
    """Provides repository instances for the admin CLI."""

    @property
    def users(self) -> UserRepository: ...

    @property
    def institutes(self) -> AdminInstituteRepository: ...

    @property
    def product_registration(self) -> ProductRegistrationRepository: ...


class AdminFactory(Protocol):
    """Cross-cutting factory for all admin CLI application service dependencies."""

    @property
    def repos(self) -> AdminRepositoryFactory: ...

    @property
    def api_key_service(self) -> AdminApiKeyService: ...

    @property
    def id_provider(self) -> IdProvider: ...

    @property
    def institute_csv_reader(self) -> InstituteCsvReaderPort: ...

    @property
    def user_cache_writer(self) -> UserCacheWriter: ...

    @property
    def institute_cache_loader(self) -> InstituteCacheLoader: ...

    @property
    def product_registration_notifier(self) -> ProductRegistrationNotifier: ...
