"""Product registration domain model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class ProductRegistration:
    """Current shared FinTS product registration."""

    product_key: str
    product_version: str
    updated_at: datetime

    def __post_init__(self) -> None:
        if not self.product_key.strip():
            raise ValueError("ProductRegistration.product_key must not be empty")
        if not self.product_version.strip():
            raise ValueError("ProductRegistration.product_version must not be empty")
