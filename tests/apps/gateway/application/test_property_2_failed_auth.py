"""Property test for failed authentication audit event (Property 2).

# Feature: audit-log, Property 2: failed auth produces consumer_auth_failed with correct consumer_id presence

Validates: Requirements 1.2, 1.3
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

import pytest
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

# Hex characters for generating key prefixes
_hex_chars = "0123456789abcdef"


@st.composite
def _disabled_consumer_strategy(draw: st.DrawFn) -> tuple[ApiConsumer, str]:
    """Generate a random disabled ApiConsumer and a key that matches its prefix."""
    consumer_id: UUID = draw(_uuid_strategy)
    email: str = draw(_email_strategy)
    suffix: str = draw(_key_suffix_strategy)
    created_at: datetime = draw(_utc_datetime_strategy)

    prefix = consumer_id.hex[:8]
    raw_key = f"{prefix}.{suffix}"

    consumer = ApiConsumer(
        consumer_id=consumer_id,
        email=email,
        api_key_hash=ApiKeyHash(raw_key),
        status=ConsumerStatus.DISABLED,
        created_at=created_at,
    )
    return consumer, raw_key


@st.composite
def _unknown_key_strategy(draw: st.DrawFn) -> tuple[str, list[ApiConsumer]]:
    """Generate a key whose prefix does not match any consumer in the cache.

    Returns the unknown raw key and a (possibly empty) list of other consumers
    whose prefixes are guaranteed to differ.
    """
    # Generate a prefix that will be used for the unknown key
    unknown_prefix: str = draw(st.text(alphabet=_hex_chars, min_size=8, max_size=8))
    suffix: str = draw(_key_suffix_strategy)
    unknown_key = f"{unknown_prefix}.{suffix}"

    # Optionally generate some other consumers whose prefixes differ
    num_others: int = draw(st.integers(min_value=0, max_value=3))
    other_consumers: list[ApiConsumer] = []
    used_prefixes = {unknown_prefix}

    for _ in range(num_others):
        consumer_id: UUID = draw(_uuid_strategy)
        prefix = consumer_id.hex[:8]
        # Skip if this consumer would accidentally match the unknown prefix
        if prefix in used_prefixes:
            continue
        used_prefixes.add(prefix)

        email: str = draw(_email_strategy)
        other_suffix: str = draw(_key_suffix_strategy)
        other_key = f"{prefix}.{other_suffix}"
        created_at: datetime = draw(_utc_datetime_strategy)

        consumer = ApiConsumer(
            consumer_id=consumer_id,
            email=email,
            api_key_hash=ApiKeyHash(other_key),
            status=ConsumerStatus.ACTIVE,
            created_at=created_at,
        )
        other_consumers.append(consumer)

    return unknown_key, other_consumers


# ---------------------------------------------------------------------------
# Stub verifier
# ---------------------------------------------------------------------------


class _StubApiKeyVerifier:
    def verify(self, presented_key: str, stored_hash: ApiKeyHash) -> bool:
        return presented_key == stored_hash.value


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_use_case(
    consumers: list[ApiConsumer],
    repo: CapturingAuditRepository,
) -> AuthenticateConsumerQuery:
    id_provider = FakeIdProvider(
        now_value=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        operation_ids=["aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"],
    )
    audit_service = AuditService(repo=repo, id_provider=id_provider)
    return AuthenticateConsumerQuery(
        consumer_cache=FakeConsumerCache(consumers),
        api_key_verifier=_StubApiKeyVerifier(),
        audit_service=audit_service,
    )


# ---------------------------------------------------------------------------
# Property 2a: Unknown key → consumer_auth_failed with consumer_id=None
# Validates: Requirements 1.2
# ---------------------------------------------------------------------------


@given(data=_unknown_key_strategy())
@settings(max_examples=100)
def test_property_2a_unknown_key_produces_consumer_auth_failed_with_no_consumer_id(
    data: tuple[str, list[ApiConsumer]],
) -> None:
    """Property 2 (unknown key sub-case): For any key whose prefix is not in the
    consumer cache, AuthenticateConsumerQuery records exactly one event with
    event_type=consumer_auth_failed and consumer_id=None.

    Validates: Requirements 1.2
    """
    # Feature: audit-log, Property 2: failed auth produces consumer_auth_failed with correct consumer_id presence
    unknown_key, other_consumers = data

    repo = CapturingAuditRepository()
    use_case = _make_use_case(other_consumers, repo)

    with pytest.raises(Exception):
        asyncio.run(use_case(unknown_key))

    assert len(repo.events) == 1
    event = repo.events[0]
    assert event.event_type == AuditEventType.CONSUMER_AUTH_FAILED
    assert event.consumer_id is None


# ---------------------------------------------------------------------------
# Property 2b: Disabled consumer → consumer_auth_failed with consumer_id present
# Validates: Requirements 1.3
# ---------------------------------------------------------------------------


@given(consumer_and_key=_disabled_consumer_strategy())
@settings(max_examples=100)
def test_property_2b_disabled_consumer_produces_consumer_auth_failed_with_consumer_id(
    consumer_and_key: tuple[ApiConsumer, str],
) -> None:
    """Property 2 (disabled consumer sub-case): For any disabled ApiConsumer and a
    key matching its prefix, AuthenticateConsumerQuery records exactly one event
    with event_type=consumer_auth_failed and consumer_id equal to the consumer's id.

    Validates: Requirements 1.3
    """
    # Feature: audit-log, Property 2: failed auth produces consumer_auth_failed with correct consumer_id presence
    consumer, raw_key = consumer_and_key

    repo = CapturingAuditRepository()
    use_case = _make_use_case([consumer], repo)

    with pytest.raises(Exception):
        asyncio.run(use_case(raw_key))

    assert len(repo.events) == 1
    event = repo.events[0]
    assert event.event_type == AuditEventType.CONSUMER_AUTH_FAILED
    assert event.consumer_id == consumer.consumer_id
