"""Product registration result DTO."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from gateway_admin.domain.entities.product import ProductRegistration


@dataclass(frozen=True)
class ProductRegistrationSummary:
    """Sanitized view of the current product registration."""

    product_key: str
    product_version: str
    updated_at: datetime


def to_product_registration_summary(
    registration: ProductRegistration,
) -> ProductRegistrationSummary:
    return ProductRegistrationSummary(
        product_key=registration.product_key,
        product_version=registration.product_version,
        updated_at=registration.updated_at,
    )
