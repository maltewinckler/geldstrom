"""Update the shared FinTS product registration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from gateway_admin.application.dtos.product_registration import (
    ProductRegistrationSummary,
    to_product_registration_summary,
)
from gateway_admin.domain.entities.product import ProductRegistration
from gateway_admin.domain.errors import ValidationError
from gateway_admin.domain.services.gateway_notifications import (
    GatewayNotificationService,
)
from gateway_admin.domain.services.identity import IdProvider

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
    ) -> None:
        self._repository = repository
        self._gateway = gateway
        self._id_provider = id_provider

    @classmethod
    def from_factory(
        cls,
        repo_factory: AdminRepositoryFactory,
        service_factory: ServiceFactory,
    ) -> Self:
        return cls(
            repository=repo_factory.product_registration,
            gateway=service_factory.gateway_notifications,
            id_provider=service_factory.id_provider,
        )

    async def __call__(
        self,
        plaintext_product_key: str,
        product_version: str,
    ) -> ProductRegistrationSummary:
        normalized_key = plaintext_product_key.strip()
        if not normalized_key:
            raise ValidationError("Product key must not be empty")

        normalized_version = product_version.strip()
        if not normalized_version:
            raise ValidationError("Product version must not be empty")

        registration = ProductRegistration(
            product_key=normalized_key,
            product_version=normalized_version,
            updated_at=self._id_provider.now(),
        )
        await self._repository.save_current(registration)
        await self._gateway.notify_product_registration_updated()
        return to_product_registration_summary(registration)
