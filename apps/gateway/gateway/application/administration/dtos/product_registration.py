"""Product registration result DTO."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from gateway.domain.product_registration import FinTSProductRegistration


@dataclass(frozen=True)
class ProductRegistrationSummary:
    """Sanitized view of the current product registration."""

    registration_id: str
    product_version: str
    key_version: str
    updated_at: datetime


def to_product_registration_summary(
    registration: FinTSProductRegistration,
) -> ProductRegistrationSummary:
    return ProductRegistrationSummary(
        registration_id=str(registration.registration_id),
        product_version=registration.product_version.value,
        key_version=registration.key_version.value,
        updated_at=registration.updated_at,
    )
