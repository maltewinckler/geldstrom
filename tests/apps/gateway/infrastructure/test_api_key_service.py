"""Tests for the Argon2 API key service."""

from gateway.domain.consumer_access import ApiKeyHash
from gateway.infrastructure.crypto import Argon2ApiKeyService


def test_generate_produces_unique_values() -> None:
    service = Argon2ApiKeyService()

    first = service.generate()
    second = service.generate()

    assert first != second
    assert first
    assert second


def test_hash_and_verify_round_trip() -> None:
    service = Argon2ApiKeyService()

    stored_hash = service.hash("raw-api-key")

    assert service.verify("raw-api-key", stored_hash) is True


def test_verify_rejects_wrong_key() -> None:
    service = Argon2ApiKeyService()

    stored_hash = ApiKeyHash(service.hash("raw-api-key").value)

    assert service.verify("other-key", stored_hash) is False
