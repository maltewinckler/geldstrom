"""Property test for token reroll audit event (Property 3).

# Feature: audit-log, Property 3: token reroll produces token_rerolled event

Validates: Requirements 3.1
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from hypothesis import given, settings
from hypothesis import strategies as st

from gateway_admin.application.commands.rotate_user_key import RotateUserKeyCommand
from gateway_admin.domain.audit.models import AuditEvent, AuditEventType
from gateway_admin.domain.users import ApiKeyHash, Email, User, UserId, UserStatus

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
# Fakes
# ---------------------------------------------------------------------------


class FakeUserRepository:
    def __init__(self, users: list[User]) -> None:
        self._users = {str(u.user_id): u for u in users}

    async def get_by_id(self, user_id: UserId) -> User | None:
        return self._users.get(str(user_id))

    async def save(self, user: User) -> None:
        self._users[str(user.user_id)] = user


class FakeApiKeyService:
    def generate(self, consumer_id: str) -> str:
        return f"{consumer_id[:8]}.fake-key"

    def hash(self, raw_key: str) -> ApiKeyHash:
        return ApiKeyHash(f"hashed::{raw_key}")


class FakeEmailService:
    async def send_token_email(self, email: str, token: str) -> None:
        pass


class FakeIdProvider:
    def __init__(self, now_value: datetime) -> None:
        self._now = now_value

    def now(self) -> datetime:
        return self._now


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_uuid_strategy = st.uuids()
_email_strategy = st.emails().filter(lambda e: len(e) <= 254)
_utc_datetime_strategy = st.datetimes(
    min_value=datetime(2000, 1, 1),
    max_value=datetime(2100, 1, 1),
    timezones=st.just(UTC),
)


@st.composite
def _active_user_strategy(draw: st.DrawFn) -> User:
    """Generate a random active User."""
    user_id: UUID = draw(_uuid_strategy)
    email: str = draw(_email_strategy)
    created_at: datetime = draw(_utc_datetime_strategy)
    return User(
        user_id=UserId(user_id),
        email=Email(email),
        api_key_hash=ApiKeyHash("initial-hash"),
        status=UserStatus.ACTIVE,
        created_at=created_at,
    )


# ---------------------------------------------------------------------------
# Property 3: Token reroll produces token_rerolled event
# Validates: Requirements 3.1
# ---------------------------------------------------------------------------


@given(user=_active_user_strategy())
@settings(max_examples=100)
def test_property_3_token_reroll_produces_token_rerolled_event(user: User) -> None:
    """Property 3: For any active consumer whose key is successfully rotated via
    RotateUserKeyCommand, the audit repository receives exactly one event with
    event_type=token_rerolled and the correct consumer_id.

    # Feature: audit-log, Property 3: token reroll produces token_rerolled event
    Validates: Requirements 3.1
    """
    audit_repo = CapturingAuditRepository()
    command = RotateUserKeyCommand(
        repository=FakeUserRepository([user]),
        api_key_service=FakeApiKeyService(),
        id_provider=FakeIdProvider(now_value=datetime(2026, 1, 1, 12, 0, tzinfo=UTC)),
        email_service=FakeEmailService(),
        audit_repository=audit_repo,
    )

    asyncio.run(command(str(user.user_id)))

    assert len(audit_repo.events) == 1
    event = audit_repo.events[0]
    assert event.event_type == AuditEventType.TOKEN_REROLLED
    assert event.consumer_id == user.user_id.value
