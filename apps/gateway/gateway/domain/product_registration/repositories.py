"""Repository contracts for product registration."""

from __future__ import annotations

from typing import Protocol

from .model import FinTSProductRegistration


class FinTSProductRegistrationRepository(Protocol):
    """Persistence contract for the current product registration."""

    async def get_current(self) -> FinTSProductRegistration | None:
        """Load the current shared product registration, if present."""

    async def save_current(self, registration: FinTSProductRegistration) -> None:
        """Persist the current shared product registration."""
