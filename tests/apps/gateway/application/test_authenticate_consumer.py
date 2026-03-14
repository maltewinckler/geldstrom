"""Tests for the AuthenticateConsumer use case."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

import pytest

from gateway.application.auth.queries.authenticate_consumer import (
    AuthenticateConsumerQuery,
)
from gateway.application.common import ForbiddenError, UnauthorizedError
from gateway.domain.consumer_access import (
    ApiConsumer,
    ApiKeyHash,
    ConsumerId,
    ConsumerStatus,
    EmailAddress,
)
from tests.apps.gateway.fakes import FakeConsumerCache


class StubApiKeyVerifier:
    def verify(self, presented_key: str, stored_hash: ApiKeyHash) -> bool:
        return presented_key == stored_hash.value


def test_authenticate_consumer_returns_identity_for_matching_active_consumer() -> None:
    consumer = _consumer(api_key_hash="key-1")
    use_case = AuthenticateConsumerQuery(FakeConsumerCache([consumer]), StubApiKeyVerifier())

    authenticated = asyncio.run(use_case("key-1"))

    assert authenticated.consumer_id == consumer.consumer_id


def test_authenticate_consumer_rejects_unknown_key() -> None:
    consumer = _consumer(api_key_hash="key-1")
    use_case = AuthenticateConsumerQuery(FakeConsumerCache([consumer]), StubApiKeyVerifier())

    with pytest.raises(UnauthorizedError, match="Invalid API key"):
        asyncio.run(use_case("missing-key"))


def test_authenticate_consumer_rejects_disabled_consumer() -> None:
    consumer = _consumer(api_key_hash="key-1", status=ConsumerStatus.DISABLED)
    use_case = AuthenticateConsumerQuery(FakeConsumerCache([consumer]), StubApiKeyVerifier())

    with pytest.raises(ForbiddenError, match="disabled"):
        asyncio.run(use_case("key-1"))


def test_authenticate_consumer_scans_multiple_consumers_until_one_matches() -> None:
    consumers = [
        _consumer(
            consumer_id="12345678-1234-5678-1234-567812345678",
            email="first@example.com",
            api_key_hash="key-1",
        ),
        _consumer(
            consumer_id="87654321-4321-8765-4321-876543218765",
            email="second@example.com",
            api_key_hash="key-2",
        ),
    ]
    use_case = AuthenticateConsumerQuery(FakeConsumerCache(consumers), StubApiKeyVerifier())

    authenticated = asyncio.run(use_case("key-2"))

    assert authenticated.consumer_id == consumers[1].consumer_id


def _consumer(
    *,
    consumer_id: str = "12345678-1234-5678-1234-567812345678",
    email: str = "consumer@example.com",
    api_key_hash: str = "key-1",
    status: ConsumerStatus = ConsumerStatus.ACTIVE,
) -> ApiConsumer:
    return ApiConsumer(
        consumer_id=ConsumerId(UUID(consumer_id)),
        email=EmailAddress(email),
        api_key_hash=ApiKeyHash(api_key_hash)
        if status is ConsumerStatus.ACTIVE
        else ApiKeyHash(api_key_hash),
        status=status,
        created_at=datetime.now(UTC),
    )
