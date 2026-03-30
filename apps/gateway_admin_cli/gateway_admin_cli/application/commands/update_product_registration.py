"""Update the shared FinTS product registration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from gateway_admin_cli.domain.errors import ValidationError
from gateway_admin_cli.domain.product import ProductRegistration

from ..dtos.product_registration import (
    ProductRegistrationSummary,
    to_product_registration_summary,
)

if TYPE_CHECKING:
    from gateway_admin_cli.application.ports.admin_factory import AdminFactory


class UpdateProductRegistrationCommand:
    """Persist the current shared product registration."""

    def __init__(
        self,
        repository,
        product_registration_notifier,
        id_provider,
        *,
        product_version: str,
    ) -> None:
        self._repository = repository
        self._product_registration_notifier = product_registration_notifier
        self._id_provider = id_provider
        self._product_version = product_version

    @classmethod
    def from_factory(
        cls,
        factory: AdminFactory,
        *,
        product_version: str,
    ) -> Self:
        return cls(
            repository=factory.repos.product_registration,
            product_registration_notifier=factory.product_registration_notifier,
            id_provider=factory.id_provider,
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
        await self._product_registration_notifier.set_current(registration)
        return to_product_registration_summary(registration)
