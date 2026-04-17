"""Property-based tests for GET /admin/users/{user_id}.

# Feature: admin-get-user-by-id

Validates: Requirements 1.1, 1.2, 1.4
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from gateway_admin.domain.users import ApiKeyHash, Email, User, UserId, UserStatus
from gateway_admin.presentation.api.routes import router

# ---------------------------------------------------------------------------
# Fake infrastructure (mirrored from test_api_get_user.py)
# ---------------------------------------------------------------------------


class FakeUserRepository:
    def __init__(self, users: list[User] | None = None) -> None:
        self._users = {str(user.user_id): user for user in users or []}

    async def list_all(self) -> list[User]:
        return sorted(self._users.values(), key=lambda u: u.email.value)

    async def get_by_id(self, user_id: UserId) -> User | None:
        return self._users.get(str(user_id))

    async def get_by_email(self, email: Email) -> User | None:
        for user in self._users.values():
            if user.email == email:
                return user
        return None

    async def save(self, user: User) -> None:
        self._users[str(user.user_id)] = user


class FakeRepoFactory:
    def __init__(self, user_repo: FakeUserRepository) -> None:
        self._users = user_repo

    @property
    def users(self) -> FakeUserRepository:
        return self._users


def _make_client(users: list[User] | None = None) -> TestClient:
    repo = FakeUserRepository(users)
    factory = FakeRepoFactory(repo)
    app = FastAPI()
    app.include_router(router, prefix="/admin")
    app.state.repo_factory = factory
    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

_utc_datetime_strategy = st.datetimes(
    min_value=datetime(2000, 1, 1),
    max_value=datetime(2100, 1, 1),
    timezones=st.just(UTC),
)

# Email strategy: generate valid emails matching the Email value object pattern
_email_strategy = st.emails().filter(
    lambda e: "@" in e and "." in e.split("@")[1] and len(e) <= 254
)

# Hash strategy: use a long enough string that it cannot accidentally appear
# in other response fields (UUID, email, status, datetime).  A 32-char
# alphanumeric string is vanishingly unlikely to be a substring of those fields.
_hash_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd")),
    min_size=32,
    max_size=64,
)

_status_strategy = st.sampled_from(list(UserStatus))


@st.composite
def _active_user_strategy(draw: st.DrawFn) -> User:
    """Generate a random active User (api_key_hash required)."""
    user_id = UserId(draw(st.uuids()))
    email = Email(draw(_email_strategy))
    api_key_hash = ApiKeyHash(draw(_hash_strategy))
    created_at = draw(_utc_datetime_strategy)
    return User(
        user_id=user_id,
        email=email,
        api_key_hash=api_key_hash,
        status=UserStatus.ACTIVE,
        created_at=created_at,
    )


@st.composite
def _user_with_hash_strategy(draw: st.DrawFn) -> User:
    """Generate a random User with a non-empty api_key_hash that is guaranteed
    not to appear in any other response field (user_id, email, status, datetime).

    We achieve this by prefixing the hash with a sentinel that cannot appear in
    those fields, then filtering to ensure the hash body doesn't accidentally
    match either.
    """
    user_id_raw: UUID = draw(st.uuids())
    email_str: str = draw(_email_strategy)
    hash_body: str = draw(_hash_strategy)
    created_at = draw(_utc_datetime_strategy)

    # Prefix with a sentinel that is not valid in UUIDs, emails, or ISO datetimes
    sentinel = "SECRETHASH:"
    full_hash = sentinel + hash_body

    # Ensure the hash body itself doesn't accidentally appear in the other fields
    other_fields = str(user_id_raw) + email_str
    assume(hash_body not in other_fields)

    return User(
        user_id=UserId(user_id_raw),
        email=Email(email_str),
        api_key_hash=ApiKeyHash(full_hash),
        status=UserStatus.ACTIVE,
        created_at=created_at,
    )


# ---------------------------------------------------------------------------
# Property 1: Lookup returns the correct user
# Feature: admin-get-user-by-id, Property 1: lookup returns the correct user
# Validates: Requirements 1.1
# ---------------------------------------------------------------------------


@given(user=_active_user_strategy())
@settings(max_examples=100)
def test_property_1_lookup_returns_correct_user(user: User) -> None:
    """For any stored user, GET /admin/users/{user_id} returns 200 and the
    response user_id matches the stored user's user_id.

    Validates: Requirements 1.1
    """
    # Feature: admin-get-user-by-id, Property 1: lookup returns the correct user
    client = _make_client([user])

    response = client.get(f"/admin/users/{user.user_id}")

    assert response.status_code == 200
    assert response.json()["user_id"] == str(user.user_id)


# ---------------------------------------------------------------------------
# Property 2: Unknown ID always returns 404
# Feature: admin-get-user-by-id, Property 2: unknown id always returns 404
# Validates: Requirements 1.2
# ---------------------------------------------------------------------------


@given(unknown_id=st.uuids())
@settings(max_examples=100)
def test_property_2_unknown_id_always_returns_404(unknown_id: UUID) -> None:
    """For any UUID not present in the repository, GET /admin/users/{id}
    always returns 404.

    Validates: Requirements 1.2
    """
    # Feature: admin-get-user-by-id, Property 2: unknown id always returns 404
    # Empty repository — no user will ever match
    client = _make_client([])

    response = client.get(f"/admin/users/{unknown_id}")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Property 3: Response never contains secret material
# Feature: admin-get-user-by-id, Property 3: response never contains secret material
# Validates: Requirements 1.4
# ---------------------------------------------------------------------------


@given(user=_user_with_hash_strategy())
@settings(max_examples=100)
def test_property_3_response_never_contains_secret_material(user: User) -> None:
    """For any stored user with a non-empty api_key_hash, the JSON response
    body does not contain that hash value.

    Validates: Requirements 1.4
    """
    # Feature: admin-get-user-by-id, Property 3: response never contains secret material
    assert user.api_key_hash is not None  # guaranteed by strategy
    secret = user.api_key_hash.value

    client = _make_client([user])
    response = client.get(f"/admin/users/{user.user_id}")

    assert response.status_code == 200
    assert secret not in response.text
