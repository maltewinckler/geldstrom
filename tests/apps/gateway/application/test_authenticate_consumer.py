"""Tests for the AuthenticateConsumer use case."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

import pytest

from gateway.application.common import ForbiddenError, UnauthorizedError
from gateway.application.consumer.queries.authenticate_consumer import (
    AuthenticateConsumerQuery,
)
from gateway.domain.consumer_access import (
    ApiConsumer,
    ApiKeyHash,
    ConsumerStatus,
)
from tests.apps.gateway.fakes import FakeConsumerCache

_CONSUMER_ID_1 = "12345678-1234-5678-1234-567812345678"
_CONSUMER_ID_2 = "87654321-4321-8765-4321-876543218765"


def _prefix(consumer_id: str) -> str:
    """Return the hex prefix for a consumer UUID."""
    return UUID(consumer_id).hex[:8]


class StubApiKeyVerifier:
    def verify(self, presented_key: str, stored_hash: ApiKeyHash) -> bool:
        return presented_key == stored_hash.value


def test_authenticate_consumer_returns_identity_for_matching_active_consumer() -> None:
    key = f"{_prefix(_CONSUMER_ID_1)}.secret-token"
    consumer = _consumer(consumer_id=_CONSUMER_ID_1, api_key_hash=key)
    use_case = AuthenticateConsumerQuery(
        FakeConsumerCache([consumer]), StubApiKeyVerifier()
    )

    authenticated = asyncio.run(use_case(key))

    assert authenticated == consumer.consumer_id


def test_authenticate_consumer_rejects_unknown_key() -> None:
    key = f"{_prefix(_CONSUMER_ID_1)}.secret-token"
    consumer = _consumer(consumer_id=_CONSUMER_ID_1, api_key_hash=key)
    use_case = AuthenticateConsumerQuery(
        FakeConsumerCache([consumer]), StubApiKeyVerifier()
    )

    with pytest.raises(UnauthorizedError, match="Invalid API key"):
        asyncio.run(use_case(f"{_prefix(_CONSUMER_ID_1)}.wrong-token"))


def test_authenticate_consumer_rejects_disabled_consumer() -> None:
    key = f"{_prefix(_CONSUMER_ID_1)}.secret-token"
    consumer = _consumer(
        consumer_id=_CONSUMER_ID_1,
        api_key_hash=key,
        status=ConsumerStatus.DISABLED,
    )
    use_case = AuthenticateConsumerQuery(
        FakeConsumerCache([consumer]), StubApiKeyVerifier()
    )

    with pytest.raises(ForbiddenError, match="disabled"):
        asyncio.run(use_case(key))


def test_authenticate_consumer_rejects_key_without_prefix() -> None:
    consumer = _consumer(consumer_id=_CONSUMER_ID_1, api_key_hash="no-prefix")
    use_case = AuthenticateConsumerQuery(
        FakeConsumerCache([consumer]), StubApiKeyVerifier()
    )

    with pytest.raises(UnauthorizedError, match="Invalid API key"):
        asyncio.run(use_case("no-prefix"))


def test_authenticate_consumer_finds_correct_consumer_by_prefix() -> None:
    key_1 = f"{_prefix(_CONSUMER_ID_1)}.token-1"
    key_2 = f"{_prefix(_CONSUMER_ID_2)}.token-2"
    consumers = [
        _consumer(
            consumer_id=_CONSUMER_ID_1,
            email="first@example.com",
            api_key_hash=key_1,
        ),
        _consumer(
            consumer_id=_CONSUMER_ID_2,
            email="second@example.com",
            api_key_hash=key_2,
        ),
    ]
    use_case = AuthenticateConsumerQuery(
        FakeConsumerCache(consumers), StubApiKeyVerifier()
    )

    authenticated = asyncio.run(use_case(key_2))

    assert authenticated == consumers[1].consumer_id


def _consumer(
    *,
    consumer_id: str = _CONSUMER_ID_1,
    email: str = "consumer@example.com",
    api_key_hash: str = "12345678.key-1",
    status: ConsumerStatus = ConsumerStatus.ACTIVE,
) -> ApiConsumer:
    return ApiConsumer(
        consumer_id=UUID(consumer_id),
        email=email,
        api_key_hash=ApiKeyHash(api_key_hash)
        if status is ConsumerStatus.ACTIVE
        else ApiKeyHash(api_key_hash),
        status=status,
        created_at=datetime.now(UTC),
    )
