"""Tests for the Argon2 API key service."""

from uuid import uuid4

from gateway.domain.consumer_access import ApiKeyHash
from gateway.infrastructure.crypto import Argon2ApiKeyService


def test_generate_produces_prefixed_key_with_unique_values() -> None:
    service = Argon2ApiKeyService()
    consumer_id = uuid4()

    first = service.generate(consumer_id)
    second = service.generate(consumer_id)

    assert first != second
    assert first
    assert second
    prefix = consumer_id.hex[:8]
    assert first.startswith(f"{prefix}.")
    assert second.startswith(f"{prefix}.")


def test_hash_and_verify_round_trip() -> None:
    service = Argon2ApiKeyService()

    stored_hash = service.hash("raw-api-key")

    assert service.verify("raw-api-key", stored_hash) is True


def test_verify_rejects_wrong_key() -> None:
    service = Argon2ApiKeyService()

    stored_hash = ApiKeyHash(service.hash("raw-api-key").value)

    assert service.verify("other-key", stored_hash) is False
