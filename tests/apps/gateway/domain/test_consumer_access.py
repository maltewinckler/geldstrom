"""Tests for the consumer access domain."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from gateway.domain.consumer_access import (
    ApiConsumer,
    ApiKeyHash,
    ConsumerId,
    ConsumerStatus,
    EmailAddress,
)
from gateway.domain.shared import DomainError


def test_email_address_is_normalized_with_casefolding() -> None:
    email = EmailAddress("User.Name@Example.COM")

    assert email.value == "user.name@example.com"


def test_email_address_rejects_invalid_input() -> None:
    with pytest.raises(DomainError, match="EmailAddress"):
        EmailAddress("not-an-email")


def test_active_consumer_must_have_hash() -> None:
    with pytest.raises(DomainError, match="ApiKeyHash"):
        ApiConsumer(
            consumer_id=ConsumerId(UUID("12345678-1234-5678-1234-567812345678")),
            email=EmailAddress("user@example.com"),
            api_key_hash=None,
            status=ConsumerStatus.ACTIVE,
            created_at=datetime.now(UTC),
        )


def test_deleted_consumer_cannot_be_reactivated_directly() -> None:
    consumer = ApiConsumer(
        consumer_id=ConsumerId(UUID("12345678-1234-5678-1234-567812345678")),
        email=EmailAddress("user@example.com"),
        api_key_hash=ApiKeyHash("argon2id$hash"),
        status=ConsumerStatus.DISABLED,
        created_at=datetime.now(UTC),
    )
    consumer.mark_deleted()

    with pytest.raises(DomainError, match="cannot be reactivated"):
        consumer.reactivate(ApiKeyHash("argon2id$new-hash"))
