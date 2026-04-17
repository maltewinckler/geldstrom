"""Unit / integration tests for GET /admin/users/{user_id}.

Validates: Requirements 1.1, 1.2, 1.4, 2.3
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from gateway_admin.domain.users import ApiKeyHash, Email, User, UserId, UserStatus
from gateway_admin.presentation.api.routes import router

# ---------------------------------------------------------------------------
# Fake infrastructure
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


# ---------------------------------------------------------------------------
# App fixture
# ---------------------------------------------------------------------------


def _make_app(repo_factory: FakeRepoFactory) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/admin")
    app.state.repo_factory = repo_factory
    return app


def _make_client(users: list[User] | None = None) -> TestClient:
    repo = FakeUserRepository(users)
    factory = FakeRepoFactory(repo)
    app = _make_app(factory)
    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user(
    *,
    user_id: str = "12345678-1234-5678-1234-567812345678",
    email: str = "consumer@example.com",
    status: UserStatus = UserStatus.ACTIVE,
    api_key_hash: str = "super-secret-hash-value",
) -> User:
    return User(
        user_id=UserId(UUID(user_id)),
        email=Email(email),
        api_key_hash=ApiKeyHash(api_key_hash),
        status=status,
        created_at=datetime(2026, 3, 12, 9, 0, tzinfo=UTC),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_get_user_found() -> None:
    """GET /admin/users/{user_id} returns 200 and correct user_id when user exists.

    Validates: Requirements 1.1
    """
    user = _user()
    client = _make_client([user])

    response = client.get(f"/admin/users/{user.user_id}")

    assert response.status_code == 200
    assert response.json()["user_id"] == str(user.user_id)


def test_get_user_not_found() -> None:
    """GET /admin/users/{unknown_id} returns 404 when no user exists.

    Validates: Requirements 1.2
    """
    client = _make_client()
    unknown_id = str(uuid4())

    response = client.get(f"/admin/users/{unknown_id}")

    assert response.status_code == 404


def test_get_user_fields_complete() -> None:
    """Response contains all required UserSummary fields.

    Validates: Requirements 2.3
    """
    user = _user()
    client = _make_client([user])

    response = client.get(f"/admin/users/{user.user_id}")

    assert response.status_code == 200
    body = response.json()
    for field in ("user_id", "email", "status", "created_at", "rotated_at"):
        assert field in body, f"Missing field: {field}"


def test_get_user_no_secret_material() -> None:
    """Response body must not contain the stored api_key_hash value.

    Validates: Requirements 1.4
    """
    secret_hash = "super-secret-hash-value"
    user = _user(api_key_hash=secret_hash)
    client = _make_client([user])

    response = client.get(f"/admin/users/{user.user_id}")

    assert response.status_code == 200
    assert secret_hash not in response.text
