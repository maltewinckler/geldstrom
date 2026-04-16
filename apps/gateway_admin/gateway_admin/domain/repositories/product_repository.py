"""Repository protocol for product registration."""

from __future__ import annotations

from typing import Protocol

from gateway_admin.domain.entities.product import ProductRegistration


class ProductRegistrationRepository(Protocol):
    async def get_current(self) -> ProductRegistration | None: ...

    async def save_current(self, registration: ProductRegistration) -> None: ...
