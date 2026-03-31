"""FinTS-specific value objects for banking gateway operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from .banking import BankLeitzahl


@dataclass
class FinTSInstitute:
    """Canonical operational institute data for gateway banking requests."""

    blz: BankLeitzahl
    bic: str | None
    name: str
    city: str | None
    organization: str | None
    pin_tan_url: str | None
    fints_version: str | None
    last_source_update: date | None

    def is_pin_tan_capable(self) -> bool:
        return self.pin_tan_url is not None


@dataclass
class FinTSProductRegistration:
    """Aggregate root containing shared product registration data."""

    product_key: str
    product_version: str
    updated_at: datetime
