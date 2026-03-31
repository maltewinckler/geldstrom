"""Tests for the consumer access domain."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from gateway.domain.consumer_access import (
    ApiConsumer,
    ApiKeyHash,
    ConsumerStatus,
)


def test_email_is_normalized_with_casefolding() -> None:
    consumer = ApiConsumer(
        consumer_id=UUID("12345678-1234-5678-1234-567812345678"),
        email="User.Name@Example.COM",
        api_key_hash=ApiKeyHash("hash"),
        status=ConsumerStatus.ACTIVE,
        created_at=datetime.now(UTC),
    )

    assert consumer.email == "user.name@example.com"


def test_email_rejects_invalid_input() -> None:
    with pytest.raises(Exception, match="not a valid email"):
        ApiConsumer(
            consumer_id=UUID("12345678-1234-5678-1234-567812345678"),
            email="not-an-email",
            api_key_hash=ApiKeyHash("hash"),
            status=ConsumerStatus.ACTIVE,
            created_at=datetime.now(UTC),
        )


def test_active_consumer_must_have_hash() -> None:
    with pytest.raises(Exception, match="ApiKeyHash"):
        ApiConsumer(
            consumer_id=UUID("12345678-1234-5678-1234-567812345678"),
            email="user@example.com",
            api_key_hash=None,
            status=ConsumerStatus.ACTIVE,
            created_at=datetime.now(UTC),
        )


def test_consumer_is_frozen() -> None:
    consumer = ApiConsumer(
        consumer_id=UUID("12345678-1234-5678-1234-567812345678"),
        email="user@example.com",
        api_key_hash=ApiKeyHash("argon2id$hash"),
        status=ConsumerStatus.ACTIVE,
        created_at=datetime.now(UTC),
    )

    with pytest.raises(Exception):
        consumer.email = "other@example.com"
