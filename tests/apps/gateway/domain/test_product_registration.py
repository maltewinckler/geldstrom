"""Tests for the product registration domain."""

from datetime import UTC, datetime

from gateway.domain.banking_gateway import FinTSProductRegistration


def test_product_registration_constructs_with_plain_product_key() -> None:
    registration = FinTSProductRegistration(
        product_key="my-product-key",
        product_version="1.0.0",
        updated_at=datetime.now(UTC),
    )

    assert registration.product_key == "my-product-key"
