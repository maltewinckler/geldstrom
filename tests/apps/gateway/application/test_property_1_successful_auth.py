"""Property test for successful authentication audit event (Property 1).

# Feature: audit-log, Property 1: successful auth produces consumer_authenticated event

Validates: Requirements 1.1
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from hypothesis import given, settings
from hypothesis import strategies as st

from gateway.application.audit.audit_service import AuditService
from gateway.application.consumer.queries.authenticate_consumer import (
    AuthenticateConsumerQuery,
)
from gateway.domain.audit import AuditEvent, AuditEventType
from gateway.domain.consumer_access import ApiConsumer, ApiKeyHash, ConsumerStatus
from tests.apps.gateway.fakes import FakeConsumerCache, FakeIdProvider

# ---------------------------------------------------------------------------
# Capturing AuditRepository
# ---------------------------------------------------------------------------


class CapturingAuditRepository:
    """In-memory AuditRepository that records all appended events."""

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def append(self, event: AuditEvent) -> None:
        self.events.append(event)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_uuid_strategy = st.uuids()

_email_strategy = st.emails().filter(lambda e: len(e) <= 254)

_key_suffix_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("Ll", "Lu", "Nd"), whitelist_characters="-_"
    ),
    min_size=8,
    max_size=32,
)

_utc_datetime_strategy = st.datetimes(
    min_value=datetime(2000, 1, 1),
    max_value=datetime(2100, 1, 1),
    timezones=st.just(UTC),
)


@st.composite
def _active_consumer_strategy(draw: st.DrawFn) -> tuple[ApiConsumer, str]:
    """Generate a random active ApiConsumer and its matching raw API key."""
    consumer_id: UUID = draw(_uuid_strategy)
    email: str = draw(_email_strategy)
    suffix: str = draw(_key_suffix_strategy)
    created_at: datetime = draw(_utc_datetime_strategy)

    # The raw key is "{hex_prefix}.{suffix}"; the hash stores the full key
    # (StubApiKeyVerifier treats hash.value == presented_key)
    prefix = consumer_id.hex[:8]
    raw_key = f"{prefix}.{suffix}"

    consumer = ApiConsumer(
        consumer_id=consumer_id,
        email=email,
        api_key_hash=ApiKeyHash(raw_key),
        status=ConsumerStatus.ACTIVE,
        created_at=created_at,
    )
    return consumer, raw_key


# ---------------------------------------------------------------------------
# Stub verifier — matches the pattern used in existing unit tests
# ---------------------------------------------------------------------------


class _StubApiKeyVerifier:
    def verify(self, presented_key: str, stored_hash: ApiKeyHash) -> bool:
        return presented_key == stored_hash.value


# ---------------------------------------------------------------------------
# Property 1: Successful auth produces consumer_authenticated event
# Validates: Requirements 1.1
# ---------------------------------------------------------------------------


@given(consumer_and_key=_active_consumer_strategy())
@settings(max_examples=100)
def test_property_1_successful_auth_produces_consumer_authenticated_event(
    consumer_and_key: tuple[ApiConsumer, str],
) -> None:
    """Property 1: For any active ApiConsumer and matching key, calling
    AuthenticateConsumerQuery records exactly one event with
    event_type=consumer_authenticated and the correct consumer_id.

    Validates: Requirements 1.1
    """
    # Feature: audit-log, Property 1: successful auth produces consumer_authenticated event
    consumer, raw_key = consumer_and_key

    repo = CapturingAuditRepository()
    id_provider = FakeIdProvider(
        now_value=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        operation_ids=["aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"],
    )
    audit_service = AuditService(repo=repo, id_provider=id_provider)

    use_case = AuthenticateConsumerQuery(
        consumer_cache=FakeConsumerCache([consumer]),
        api_key_verifier=_StubApiKeyVerifier(),
        audit_service=audit_service,
    )

    result = asyncio.run(use_case(raw_key))

    # Primary operation succeeds
    assert result == consumer.consumer_id

    # Exactly one audit event recorded
    assert len(repo.events) == 1

    event = repo.events[0]
    assert event.event_type == AuditEventType.CONSUMER_AUTHENTICATED
    assert event.consumer_id == consumer.consumer_id
