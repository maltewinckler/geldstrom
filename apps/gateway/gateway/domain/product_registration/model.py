"""Aggregate for encrypted product registration data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from gateway.domain.shared import EntityId

from .value_objects import EncryptedProductKey, KeyVersion, ProductVersion


@dataclass
class FinTSProductRegistration:
    """Aggregate root containing encrypted shared product registration data."""

    registration_id: EntityId
    encrypted_product_key: EncryptedProductKey
    product_version: ProductVersion
    key_version: KeyVersion
    updated_at: datetime
