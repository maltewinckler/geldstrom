"""Product key encryption port."""

from __future__ import annotations

from typing import Protocol

from gateway.domain.product_registration import EncryptedProductKey


class ProductKeyEncryptor(Protocol):
    """Encrypts plaintext product key material for storage."""

    def encrypt(self, plaintext: str) -> EncryptedProductKey: ...
