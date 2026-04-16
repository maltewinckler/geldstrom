"""Gateway notification service abstract base class."""

from __future__ import annotations

from abc import ABC, abstractmethod


class GatewayNotificationService(ABC):
    """Signals the running gateway process to invalidate or reload its in-memory caches."""

    @abstractmethod
    async def notify_user_updated(self, user_id: str) -> None: ...

    @abstractmethod
    async def notify_institute_catalog_replaced(self) -> None: ...

    @abstractmethod
    async def notify_product_registration_updated(self) -> None: ...
