"""Tests for the product key encryption service."""

import pytest

from gateway.application.common import InternalError
from gateway.infrastructure.crypto import ProductKeyService


def test_encrypt_and_decrypt_round_trip() -> None:
    service = ProductKeyService("master-key")

    encrypted = service.encrypt("product-key-1")

    assert encrypted.value != b"product-key-1"
    assert service.decrypt(encrypted) == "product-key-1"


def test_wrong_master_key_fails_decryption() -> None:
    first = ProductKeyService("master-key-a")
    second = ProductKeyService("master-key-b")

    encrypted = first.encrypt("product-key-1")

    with pytest.raises(InternalError, match="Unable to decrypt product key"):
        second.decrypt(encrypted)
