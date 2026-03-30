"""Outbound ports for the admin CLI application layer."""

from .admin_factory import AdminFactory, AdminRepositoryFactory
from .institute_repository import AdminInstituteRepository
from .product_repository import ProductRegistrationRepository
from .services import (
    AdminApiKeyService,
    IdProvider,
    InstituteCacheLoader,
    InstituteCsvReaderPort,
    ProductKeyEncryptor,
    ProductRegistrationNotifier,
    UserCacheWriter,
)
from .user_repository import UserRepository

__all__ = [
    "AdminFactory",
    "AdminInstituteRepository",
    "AdminRepositoryFactory",
    "AdminApiKeyService",
    "IdProvider",
    "InstituteCacheLoader",
    "InstituteCsvReaderPort",
    "ProductKeyEncryptor",
    "ProductRegistrationNotifier",
    "ProductRegistrationRepository",
    "UserCacheWriter",
    "UserRepository",
]
