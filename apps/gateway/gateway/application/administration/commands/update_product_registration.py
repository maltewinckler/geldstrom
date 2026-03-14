"""Update the shared FinTS product registration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self
from uuid import UUID

from gateway.application.common import IdProvider, ValidationError
from gateway.domain.product_registration import (
    FinTSProductRegistration,
    FinTSProductRegistrationRepository,
    KeyVersion,
    ProductVersion,
)
from gateway.domain.shared import EntityId

from ..dtos.product_registration import (
    ProductRegistrationSummary,
    to_product_registration_summary,
)
from ..ports.product_key_encryptor import ProductKeyEncryptor
from ..ports.product_key_loader import CurrentProductKeyLoader
from ..ports.product_registration_cache import ProductRegistrationCachePort

if TYPE_CHECKING:
    from gateway.application.ports import ApplicationFactory


class UpdateProductRegistrationCommand:
    """Encrypt and persist the current shared product registration."""

    def __init__(
        self,
        repository: FinTSProductRegistrationRepository,
        product_registration_cache: ProductRegistrationCachePort,
        current_product_key_provider: CurrentProductKeyLoader,
        product_key_service: ProductKeyEncryptor,
        id_provider: IdProvider,
        *,
        product_version: str,
        key_version: str,
    ) -> None:
        self._repository = repository
        self._product_registration_cache = product_registration_cache
        self._current_product_key_provider = current_product_key_provider
        self._product_key_service = product_key_service
        self._id_provider = id_provider
        self._product_version = ProductVersion(product_version)
        self._key_version = KeyVersion(key_version)

    @classmethod
    def from_factory(
        cls,
        factory: ApplicationFactory,
        *,
        product_version: str,
        key_version: str,
    ) -> Self:
        return cls(
            repository=factory.repos.product_registration,
            product_registration_cache=factory.caches.product_registration,
            current_product_key_provider=factory.caches.product_key,
            product_key_service=factory.product_key_encryptor,
            id_provider=factory.id_provider,
            product_version=product_version,
            key_version=key_version,
        )

    async def __call__(self, plaintext_product_key: str) -> ProductRegistrationSummary:
        normalized_key = plaintext_product_key.strip()
        if not normalized_key:
            raise ValidationError("Product key must not be empty")

        registration = FinTSProductRegistration(
            registration_id=EntityId(UUID(self._id_provider.new_operation_id())),
            encrypted_product_key=self._product_key_service.encrypt(normalized_key),
            product_version=self._product_version,
            key_version=self._key_version,
            updated_at=self._id_provider.now(),
        )
        await self._repository.save_current(registration)
        await self._product_registration_cache.set_current(registration)
        await self._current_product_key_provider.load_current(normalized_key)
        return to_product_registration_summary(registration)
