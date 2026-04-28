"""Gateway notification service abstract base class."""

from __future__ import annotations

from abc import ABC, abstractmethod


class GatewayNotificationService(ABC):
    """Signals the running gateway process to reload its in-memory caches."""

    @abstractmethod
    async def notify_institute_catalog_replaced(self) -> None: ...

    @abstractmethod
    async def notify_product_registration_updated(self) -> None: ...
