"""Tests for the product registration domain."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from gateway.domain.product_registration import (
    EncryptedProductKey,
    FinTSProductRegistration,
    KeyVersion,
    ProductVersion,
)
from gateway.domain.shared import DomainError, EntityId


def test_product_registration_constructs_with_encrypted_key_material() -> None:
    registration = FinTSProductRegistration(
        registration_id=EntityId(UUID("12345678-1234-5678-1234-567812345678")),
        encrypted_product_key=EncryptedProductKey(b"ciphertext"),
        product_version=ProductVersion("1.0.0"),
        key_version=KeyVersion("2026-03"),
        updated_at=datetime.now(UTC),
    )

    assert registration.encrypted_product_key.value == b"ciphertext"


def test_encrypted_product_key_must_not_be_empty() -> None:
    with pytest.raises(DomainError, match="must not be empty"):
        EncryptedProductKey(b"")


def test_version_value_objects_must_not_be_empty() -> None:
    with pytest.raises(DomainError, match="ProductVersion"):
        ProductVersion(" ")

    with pytest.raises(DomainError, match="KeyVersion"):
        KeyVersion("")
