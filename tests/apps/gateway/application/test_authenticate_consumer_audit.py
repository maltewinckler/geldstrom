"""Unit tests for AuthenticateConsumerQuery audit integration.

Verifies that audit_service.record() is called with the correct arguments
for each authentication outcome.

Requirements: 1.1, 1.2, 1.3
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

import pytest

from gateway.application.common import ForbiddenError, UnauthorizedError
from gateway.application.consumer.queries.authenticate_consumer import (
    AuthenticateConsumerQuery,
)
from gateway.domain.audit import AuditEventType
from gateway.domain.consumer_access import ApiConsumer, ApiKeyHash, ConsumerStatus
from tests.apps.gateway.fakes import FakeAuditService, FakeConsumerRepository

_CONSUMER_ID = UUID("12345678-1234-5678-1234-567812345678")
_KEY_PREFIX = _CONSUMER_ID.hex[:8]
_VALID_KEY = f"{_KEY_PREFIX}.secret-token"


class StubApiKeyVerifier:
    def verify(self, presented_key: str, stored_hash: ApiKeyHash) -> bool:
        return presented_key == stored_hash.value


def _active_consumer(
    consumer_id: UUID = _CONSUMER_ID,
    api_key_hash: str = _VALID_KEY,
) -> ApiConsumer:
    return ApiConsumer(
        consumer_id=consumer_id,
        email="consumer@example.com",
        api_key_hash=ApiKeyHash(api_key_hash),
        status=ConsumerStatus.ACTIVE,
        created_at=datetime.now(UTC),
    )


def _disabled_consumer(
    consumer_id: UUID = _CONSUMER_ID,
    api_key_hash: str = _VALID_KEY,
) -> ApiConsumer:
    return ApiConsumer(
        consumer_id=consumer_id,
        email="consumer@example.com",
        api_key_hash=ApiKeyHash(api_key_hash),
        status=ConsumerStatus.DISABLED,
        created_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Requirement 1.1 — successful authentication
# ---------------------------------------------------------------------------


def test_audit_record_called_with_consumer_authenticated_on_success() -> None:
    audit = FakeAuditService()
    use_case = AuthenticateConsumerQuery(
        FakeConsumerRepository([_active_consumer()]),
        StubApiKeyVerifier(),
        audit,
    )

    asyncio.run(use_case(_VALID_KEY))

    assert len(audit.recorded) == 1
    event_type, consumer_id = audit.recorded[0]
    assert event_type == AuditEventType.CONSUMER_AUTHENTICATED
    assert consumer_id == _CONSUMER_ID


# ---------------------------------------------------------------------------
# Requirement 1.2 — unknown-key failure (consumer_id must be None)
# ---------------------------------------------------------------------------


def test_audit_record_called_with_consumer_auth_failed_and_none_on_unknown_key() -> (
    None
):
    audit = FakeAuditService()
    use_case = AuthenticateConsumerQuery(
        FakeConsumerRepository([_active_consumer()]),
        StubApiKeyVerifier(),
        audit,
    )

    with pytest.raises(UnauthorizedError):
        asyncio.run(use_case(f"{_KEY_PREFIX}.wrong-token"))

    assert len(audit.recorded) == 1
    event_type, consumer_id = audit.recorded[0]
    assert event_type == AuditEventType.CONSUMER_AUTH_FAILED
    assert consumer_id is None


def test_audit_record_called_with_none_consumer_id_when_prefix_not_found() -> None:
    """Key prefix doesn't match any consumer — consumer is completely unknown."""
    audit = FakeAuditService()
    use_case = AuthenticateConsumerQuery(
        FakeConsumerRepository([]),  # empty cache
        StubApiKeyVerifier(),
        audit,
    )

    with pytest.raises(UnauthorizedError):
        asyncio.run(use_case(_VALID_KEY))

    assert len(audit.recorded) == 1
    event_type, consumer_id = audit.recorded[0]
    assert event_type == AuditEventType.CONSUMER_AUTH_FAILED
    assert consumer_id is None


# ---------------------------------------------------------------------------
# Requirement 1.3 — disabled-consumer failure (consumer_id must be present)
# ---------------------------------------------------------------------------


def test_audit_record_called_with_consumer_auth_failed_and_consumer_id_on_disabled() -> (
    None
):
    audit = FakeAuditService()
    use_case = AuthenticateConsumerQuery(
        FakeConsumerRepository([_disabled_consumer()]),
        StubApiKeyVerifier(),
        audit,
    )

    with pytest.raises(ForbiddenError):
        asyncio.run(use_case(_VALID_KEY))

    assert len(audit.recorded) == 1
    event_type, consumer_id = audit.recorded[0]
    assert event_type == AuditEventType.CONSUMER_AUTH_FAILED
    assert consumer_id == _CONSUMER_ID


def test_audit_record_uses_correct_consumer_id_for_disabled_consumer() -> None:
    """Ensures the consumer_id in the audit event matches the disabled consumer's id."""
    other_id = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    other_prefix = other_id.hex[:8]
    other_key = f"{other_prefix}.other-token"

    audit = FakeAuditService()
    use_case = AuthenticateConsumerQuery(
        FakeConsumerRepository(
            [_disabled_consumer(consumer_id=other_id, api_key_hash=other_key)]
        ),
        StubApiKeyVerifier(),
        audit,
    )

    with pytest.raises(ForbiddenError):
        asyncio.run(use_case(other_key))

    assert len(audit.recorded) == 1
    event_type, consumer_id = audit.recorded[0]
    assert event_type == AuditEventType.CONSUMER_AUTH_FAILED
    assert consumer_id == other_id


# ---------------------------------------------------------------------------
# Exactly one audit event per call
# ---------------------------------------------------------------------------


def test_exactly_one_audit_event_recorded_per_authentication_call() -> None:
    audit = FakeAuditService()
    use_case = AuthenticateConsumerQuery(
        FakeConsumerRepository([_active_consumer()]),
        StubApiKeyVerifier(),
        audit,
    )

    asyncio.run(use_case(_VALID_KEY))

    assert len(audit.recorded) == 1
