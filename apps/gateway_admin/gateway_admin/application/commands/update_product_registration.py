"""Update the shared FinTS product registration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from gateway_admin.domain.entities.product import ProductRegistration
from gateway_admin.domain.errors import ValidationError
from gateway_admin.domain.services.gateway_notifications import (
    GatewayNotificationService,
)
from gateway_admin.domain.services.identity import IdProvider

from ..dtos.product_registration import (
    ProductRegistrationSummary,
    to_product_registration_summary,
)

if TYPE_CHECKING:
    from gateway_admin.application.factories.admin_factory import AdminRepositoryFactory
    from gateway_admin.application.factories.service_factory import ServiceFactory


class UpdateProductRegistrationCommand:
    """Persist the current shared product registration and notify the gateway."""

    def __init__(
        self,
        repository,
        gateway: GatewayNotificationService,
        id_provider: IdProvider,
        *,
        product_version: str,
    ) -> None:
        self._repository = repository
        self._gateway = gateway
        self._id_provider = id_provider
        self._product_version = product_version

    @classmethod
    def from_factory(
        cls,
        repo_factory: AdminRepositoryFactory,
        service_factory: ServiceFactory,
        *,
        product_version: str,
    ) -> Self:
        return cls(
            repository=repo_factory.product_registration,
            gateway=service_factory.gateway_notifications,
            id_provider=service_factory.id_provider,
            product_version=product_version,
        )

    async def __call__(self, plaintext_product_key: str) -> ProductRegistrationSummary:
        normalized_key = plaintext_product_key.strip()
        if not normalized_key:
            raise ValidationError("Product key must not be empty")

        registration = ProductRegistration(
            product_key=normalized_key,
            product_version=self._product_version,
            updated_at=self._id_provider.now(),
        )
        await self._repository.save_current(registration)
        await self._gateway.notify_product_registration_updated()
        return to_product_registration_summary(registration)
