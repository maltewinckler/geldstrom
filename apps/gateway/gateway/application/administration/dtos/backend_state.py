"""Backend state report DTO."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from gateway.domain.institution_catalog import FinTSInstitute

from .product_registration import ProductRegistrationSummary


@dataclass(frozen=True)
class BackendStateReport:
    """Sanitized backend state snapshot for operator inspection."""

    health: dict[str, Any]
    total_consumer_count: int
    active_consumer_count: int
    institute_count: int
    selected_institute: FinTSInstitute | None = None
    product_registration: ProductRegistrationSummary | None = None
