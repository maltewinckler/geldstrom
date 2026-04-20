"""Get the current FinTS product registration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from gateway_admin.domain.entities.product import ProductRegistration

if TYPE_CHECKING:
    from gateway_admin.application.factories.admin_factory import AdminRepositoryFactory
    from gateway_admin.domain.repositories.product_repository import (
        ProductRegistrationRepository,
    )


class GetProductRegistrationQuery:
    """Return the current product registration singleton, or None if absent."""

    def __init__(self, repository: ProductRegistrationRepository) -> None:
        self._repository = repository

    @classmethod
    def from_factory(cls, repo_factory: AdminRepositoryFactory) -> Self:
        return cls(repo_factory.product_registration)

    async def __call__(self) -> ProductRegistration | None:
        return await self._repository.get_current()
