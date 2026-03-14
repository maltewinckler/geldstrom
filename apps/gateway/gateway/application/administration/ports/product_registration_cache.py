"""Product registration cache port."""

from __future__ import annotations

from typing import Protocol

from gateway.domain.product_registration import FinTSProductRegistration


class ProductRegistrationCachePort(Protocol):
    """Stores the current product registration in memory."""

    async def set_current(
        self, registration: FinTSProductRegistration | None
    ) -> None: ...
