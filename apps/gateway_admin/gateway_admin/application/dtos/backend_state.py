"""Backend state report DTO."""

from __future__ import annotations

from dataclasses import dataclass

from gateway_admin.domain.entities.institutes import FinTSInstitute

from .product_registration import ProductRegistrationSummary


@dataclass(frozen=True)
class BackendStateReport:
    """Sanitized backend state snapshot for operator inspection."""

    db_connectivity: str
    total_user_count: int
    active_user_count: int
    institute_count: int
    selected_institute: FinTSInstitute | None = None
    product_registration: ProductRegistrationSummary | None = None
