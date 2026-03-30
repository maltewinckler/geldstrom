"""Repository port for product registration."""

from __future__ import annotations

from typing import Protocol

from gateway_admin_cli.domain.product import ProductRegistration


class ProductRegistrationRepository(Protocol):
    """Persistence contract for the shared FinTS product registration."""

    async def get_current(self) -> ProductRegistration | None: ...

    async def save_current(self, registration: ProductRegistration) -> None: ...
