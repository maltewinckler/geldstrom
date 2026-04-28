"""Tests for all /admin/users API endpoints.

Covers unit tests and property-based tests for:
- GET /admin/users
- POST /admin/users
- POST /admin/users/{user_id}/reroll
- POST /admin/users/{user_id}/disable
- POST /admin/users/{user_id}/reactivate
- DELETE /admin/users/{user_id}
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient
from hypothesis import given, settings
from hypothesis import strategies as st

from gateway_admin.domain.entities.users import User, UserStatus
from gateway_admin.domain.value_objects.user import ApiKeyHash, Email, UserId
from gateway_admin.infrastructure.services.email_service import MockEmailService
from gateway_admin.presentation.api.dependencies import (
    get_repo_factory,
    get_service_factory,
)
from gateway_admin.presentation.api.main import app

from .conftest import (
    InMemoryUserRepository,
    MockAdminRepositoryFactory,
    MockServiceFactory,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REQUIRED_USER_FIELDS = {"user_id", "email", "status", "created_at"}


def _make_user(
    email: str = "test@example.com",
    status: UserStatus = UserStatus.ACTIVE,
) -> User:
    uid = UserId(uuid4())
    return User(
        user_id=uid,
        email=Email(email),
        api_key_hash=ApiKeyHash("$test$hash") if status == UserStatus.ACTIVE else None,
        status=status,
        created_at=datetime.now(UTC),
        rotated_at=None,
    )


def _make_repo_with_users(
    *users: User,
) -> tuple[MockAdminRepositoryFactory, MockServiceFactory, MockEmailService]:
    email_svc = MockEmailService()
    repo = InMemoryUserRepository()
    repo_factory = MockAdminRepositoryFactory(user_repo=repo)
    svc_factory = MockServiceFactory(email_svc=email_svc)
    for user in users:
        asyncio.run(repo.save(user))
    return repo_factory, svc_factory, email_svc


def _override_deps(
    repo_factory: MockAdminRepositoryFactory,
    svc_factory: MockServiceFactory,
) -> None:
    app.dependency_overrides[get_repo_factory] = lambda: repo_factory
    app.dependency_overrides[get_service_factory] = lambda: svc_factory


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# GET /admin/users
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_users_empty(client: AsyncClient) -> None:
    """GET /admin/users returns 200 with empty list when no users exist."""
    response = await client.get("/admin/users")
    assert response.status_code == 200
    data = response.json()
    assert data["users"] == []


@pytest.mark.asyncio
async def test_list_users_returns_required_fields(
    client: AsyncClient, mock_repo_factory: MockAdminRepositoryFactory
) -> None:
    """GET /admin/users returns users with all required fields."""
    user = _make_user("alice@example.com")
    await mock_repo_factory.users.save(user)

    response = await client.get("/admin/users")
    assert response.status_code == 200
    users = response.json()["users"]
    assert len(users) == 1
    u = users[0]
    for field in _REQUIRED_USER_FIELDS:
        assert field in u, f"Missing field: {field}"
        assert u[field] is not None, f"Field {field} must not be null"


@pytest.mark.asyncio
async def test_list_users_sorted_alphabetically(
    client: AsyncClient, mock_repo_factory: MockAdminRepositoryFactory
) -> None:
    """GET /admin/users returns users sorted alphabetically by email."""
    for email in ["charlie@example.com", "alice@example.com", "bob@example.com"]:
        await mock_repo_factory.users.save(_make_user(email))

    response = await client.get("/admin/users")
    assert response.status_code == 200
    emails = [u["email"] for u in response.json()["users"]]
    assert emails == sorted(emails)


# ---------------------------------------------------------------------------
# Property 1: User list is alphabetically sorted
# Validates: Requirements 1.4
# ---------------------------------------------------------------------------

_email_strategy = st.emails().filter(lambda e: len(e) < 100)


@given(emails=st.lists(_email_strategy, min_size=1, max_size=10, unique=True))
@settings(max_examples=50)
def test_property_1_user_list_sorted(emails: list[str]) -> None:
    """Property 1: For any set of users, GET /admin/users returns them sorted by email.

    Validates: Requirements 1.4
    """
    from httpx import ASGITransport

    email_svc = MockEmailService()
    repo = InMemoryUserRepository()
    factory = MockAdminRepositoryFactory(user_repo=repo)
    svc_factory = MockServiceFactory(email_svc=email_svc)

    for email in emails:
        try:
            user = _make_user(email)
            asyncio.run(repo.save(user))
        except Exception:
            pass  # skip invalid emails generated by hypothesis

    _override_deps(factory, svc_factory)
    try:
        transport = ASGITransport(app=app)

        async def _run() -> list[str]:
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/admin/users")
                return [u["email"] for u in resp.json()["users"]]

        returned_emails = asyncio.run(_run())
        assert returned_emails == sorted(e.lower() for e in returned_emails)
    finally:
        _clear_overrides()


# ---------------------------------------------------------------------------
# Property 2: User details are complete
# Validates: Requirements 1.3
# ---------------------------------------------------------------------------


@given(emails=st.lists(_email_strategy, min_size=1, max_size=5, unique=True))
@settings(max_examples=50)
def test_property_2_user_details_complete(emails: list[str]) -> None:
    """Property 2: Every user in the response has all required fields non-null.

    Validates: Requirements 1.3
    """
    from httpx import ASGITransport

    email_svc = MockEmailService()
    repo = InMemoryUserRepository()
    factory = MockAdminRepositoryFactory(user_repo=repo)
    svc_factory = MockServiceFactory(email_svc=email_svc)

    for email in emails:
        try:
            user = _make_user(email)
            asyncio.run(repo.save(user))
        except Exception:
            pass

    _override_deps(factory, svc_factory)
    try:
        transport = ASGITransport(app=app)

        async def _run() -> list[dict[str, Any]]:
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.get("/admin/users")
                return resp.json()["users"]

        users = asyncio.run(_run())
        for u in users:
            for field in _REQUIRED_USER_FIELDS:
                assert field in u
                assert u[field] is not None
    finally:
        _clear_overrides()


# ---------------------------------------------------------------------------
# POST /admin/users
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_user_success(
    client: AsyncClient, mock_email_service: MockEmailService
) -> None:
    """POST /admin/users returns 201 and message says token sent."""
    response = await client.post("/admin/users", json={"email": "new@example.com"})
    assert response.status_code == 201
    data = response.json()
    assert "token" in data["message"].lower() or "sent" in data["message"].lower()
    assert data["user"]["email"] == "new@example.com"


@pytest.mark.asyncio
async def test_create_user_duplicate_email(client: AsyncClient) -> None:
    """POST /admin/users returns 400 on duplicate email."""
    await client.post("/admin/users", json={"email": "dup@example.com"})
    response = await client.post("/admin/users", json={"email": "dup@example.com"})
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_user_invalid_email(client: AsyncClient) -> None:
    """POST /admin/users returns 422 on invalid email format."""
    response = await client.post("/admin/users", json={"email": "not-an-email"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_user_token_not_in_response(
    client: AsyncClient, mock_email_service: MockEmailService
) -> None:
    """POST /admin/users: token must not appear in the response body."""
    response = await client.post("/admin/users", json={"email": "safe@example.com"})
    assert response.status_code == 201
    # The actual token was sent via email; grab it
    assert len(mock_email_service.sent_emails) == 1
    token = mock_email_service.sent_emails[0].body
    response_text = response.text
    assert token not in response_text


# ---------------------------------------------------------------------------
# Property 3: Create user generates token and sends email
# Validates: Requirements 3.4, 3.5, 3.6, 9.1, 9.3
# ---------------------------------------------------------------------------


@given(email=_email_strategy)
@settings(max_examples=50)
def test_property_3_create_user_sends_email(email: str) -> None:
    """Property 3: For any valid email, creating a user sends exactly one email.

    Validates: Requirements 3.4, 3.5, 3.6, 9.1, 9.3
    """
    from httpx import ASGITransport

    email_svc = MockEmailService()
    repo = InMemoryUserRepository()
    factory = MockAdminRepositoryFactory(user_repo=repo)
    svc_factory = MockServiceFactory(email_svc=email_svc)
    _override_deps(factory, svc_factory)
    try:
        transport = ASGITransport(app=app)

        async def _run() -> int:
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post("/admin/users", json={"email": email})
                return resp.status_code

        status_code = asyncio.run(_run())
        if status_code == 201:
            assert len(email_svc.sent_emails) == 1
            # The email is sent to the normalized (lowercased) version of the address
            sent_to = email_svc.sent_emails[0].to
            assert "@" in sent_to
    finally:
        _clear_overrides()


# ---------------------------------------------------------------------------
# Property 4: Duplicate email is rejected
# Validates: Requirements 3.7
# ---------------------------------------------------------------------------


@given(email=_email_strategy)
@settings(max_examples=50)
def test_property_4_duplicate_email_rejected(email: str) -> None:
    """Property 4: Duplicate email always results in 400.

    Validates: Requirements 3.7
    """
    from httpx import ASGITransport

    email_svc = MockEmailService()
    repo = InMemoryUserRepository()
    factory = MockAdminRepositoryFactory(user_repo=repo)
    svc_factory = MockServiceFactory(email_svc=email_svc)
    _override_deps(factory, svc_factory)
    try:
        transport = ASGITransport(app=app)

        async def _run() -> tuple[int, int]:
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                r1 = await ac.post("/admin/users", json={"email": email})
                r2 = await ac.post("/admin/users", json={"email": email})
                return r1.status_code, r2.status_code

        s1, s2 = asyncio.run(_run())
        if s1 == 201:
            assert s2 == 400
    finally:
        _clear_overrides()


# ---------------------------------------------------------------------------
# Property 6: Token never in response (create)
# Validates: Requirements 2.6, 3.8
# ---------------------------------------------------------------------------


@given(email=_email_strategy)
@settings(max_examples=50)
def test_property_6_token_not_in_create_response(email: str) -> None:
    """Property 6: Token is never returned in the create user response.

    Validates: Requirements 2.6, 3.8
    """
    from httpx import ASGITransport

    email_svc = MockEmailService()
    repo = InMemoryUserRepository()
    factory = MockAdminRepositoryFactory(user_repo=repo)
    svc_factory = MockServiceFactory(email_svc=email_svc)
    _override_deps(factory, svc_factory)
    try:
        transport = ASGITransport(app=app)

        async def _run() -> tuple[int, str, str]:
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post("/admin/users", json={"email": email})
                token = email_svc.sent_emails[0].body if email_svc.sent_emails else ""
                return resp.status_code, resp.text, token

        status_code, body, token = asyncio.run(_run())
        if status_code == 201 and token:
            assert token not in body
    finally:
        _clear_overrides()


# ---------------------------------------------------------------------------
# POST /admin/users/{user_id}/reroll
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reroll_active_user(
    client: AsyncClient,
    mock_repo_factory: MockAdminRepositoryFactory,
    mock_email_service: MockEmailService,
) -> None:
    """POST /admin/users/{user_id}/reroll returns 200 for active user."""
    user = _make_user("reroll@example.com", UserStatus.ACTIVE)
    await mock_repo_factory.users.save(user)

    response = await client.post(f"/admin/users/{user.user_id}/reroll")
    assert response.status_code == 200
    data = response.json()
    assert "token" in data["message"].lower() or "sent" in data["message"].lower()


@pytest.mark.asyncio
async def test_reroll_deleted_user_returns_400(
    client: AsyncClient, mock_repo_factory: MockAdminRepositoryFactory
) -> None:
    """POST /admin/users/{user_id}/reroll returns 400 for deleted user."""
    user = _make_user("deleted@example.com", UserStatus.DELETED)
    await mock_repo_factory.users.save(user)

    response = await client.post(f"/admin/users/{user.user_id}/reroll")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_reroll_token_not_in_response(
    client: AsyncClient,
    mock_repo_factory: MockAdminRepositoryFactory,
    mock_email_service: MockEmailService,
) -> None:
    """POST /admin/users/{user_id}/reroll: token must not appear in response."""
    user = _make_user("reroll2@example.com", UserStatus.ACTIVE)
    await mock_repo_factory.users.save(user)

    response = await client.post(f"/admin/users/{user.user_id}/reroll")
    assert response.status_code == 200
    assert len(mock_email_service.sent_emails) == 1
    token = mock_email_service.sent_emails[0].body
    assert token not in response.text


# ---------------------------------------------------------------------------
# Property 5: Reroll generates new token and sends email
# Validates: Requirements 2.3, 2.4, 2.5, 9.2, 9.3
# ---------------------------------------------------------------------------


@given(email=_email_strategy)
@settings(max_examples=50)
def test_property_5_reroll_sends_email(email: str) -> None:
    """Property 5: For any active user, reroll sends exactly one email.

    Validates: Requirements 2.3, 2.4, 2.5, 9.2, 9.3
    """
    from httpx import ASGITransport

    email_svc = MockEmailService()
    repo = InMemoryUserRepository()
    factory = MockAdminRepositoryFactory(user_repo=repo)
    svc_factory = MockServiceFactory(email_svc=email_svc)

    try:
        user = _make_user(email, UserStatus.ACTIVE)
    except Exception:
        return  # skip invalid emails

    asyncio.run(repo.save(user))
    _override_deps(factory, svc_factory)
    try:
        transport = ASGITransport(app=app)

        async def _run() -> int:
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post(f"/admin/users/{user.user_id}/reroll")
                return resp.status_code

        status_code = asyncio.run(_run())
        assert status_code == 200
        assert len(email_svc.sent_emails) == 1
    finally:
        _clear_overrides()


# ---------------------------------------------------------------------------
# Property 6 (reroll): Token never in response
# Validates: Requirements 2.6
# ---------------------------------------------------------------------------


@given(email=_email_strategy)
@settings(max_examples=50)
def test_property_6_token_not_in_reroll_response(email: str) -> None:
    """Property 6: Token is never returned in the reroll response.

    Validates: Requirements 2.6
    """
    from httpx import ASGITransport

    email_svc = MockEmailService()
    repo = InMemoryUserRepository()
    factory = MockAdminRepositoryFactory(user_repo=repo)
    svc_factory = MockServiceFactory(email_svc=email_svc)

    try:
        user = _make_user(email, UserStatus.ACTIVE)
    except Exception:
        return

    asyncio.run(repo.save(user))
    _override_deps(factory, svc_factory)
    try:
        transport = ASGITransport(app=app)

        async def _run() -> tuple[int, str, str]:
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post(f"/admin/users/{user.user_id}/reroll")
                token = email_svc.sent_emails[0].body if email_svc.sent_emails else ""
                return resp.status_code, resp.text, token

        status_code, body, token = asyncio.run(_run())
        if status_code == 200 and token:
            assert token not in body
    finally:
        _clear_overrides()


# ---------------------------------------------------------------------------
# Property 10: Cannot reroll deleted user
# Validates: Requirements 2.7
# ---------------------------------------------------------------------------


@given(email=_email_strategy)
@settings(max_examples=50)
def test_property_10_cannot_reroll_deleted_user(email: str) -> None:
    """Property 10: Rerolling a deleted user always returns 400.

    Validates: Requirements 2.7
    """
    from httpx import ASGITransport

    email_svc = MockEmailService()
    repo = InMemoryUserRepository()
    factory = MockAdminRepositoryFactory(user_repo=repo)
    svc_factory = MockServiceFactory(email_svc=email_svc)

    try:
        user = _make_user(email, UserStatus.DELETED)
    except Exception:
        return

    asyncio.run(repo.save(user))
    _override_deps(factory, svc_factory)
    try:
        transport = ASGITransport(app=app)

        async def _run() -> int:
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post(f"/admin/users/{user.user_id}/reroll")
                return resp.status_code

        status_code = asyncio.run(_run())
        assert status_code == 400
    finally:
        _clear_overrides()


# ---------------------------------------------------------------------------
# POST /admin/users/{user_id}/disable
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_disable_active_user(
    client: AsyncClient, mock_repo_factory: MockAdminRepositoryFactory
) -> None:
    """POST /admin/users/{user_id}/disable returns 200 and status becomes disabled."""
    user = _make_user("active@example.com", UserStatus.ACTIVE)
    await mock_repo_factory.users.save(user)

    response = await client.post(f"/admin/users/{user.user_id}/disable")
    assert response.status_code == 200
    assert response.json()["status"] == "disabled"


@pytest.mark.asyncio
async def test_disable_already_disabled_user(
    client: AsyncClient, mock_repo_factory: MockAdminRepositoryFactory
) -> None:
    """POST /admin/users/{user_id}/disable returns 400 on already disabled user."""
    user = _make_user("disabled@example.com", UserStatus.DISABLED)
    await mock_repo_factory.users.save(user)

    response = await client.post(f"/admin/users/{user.user_id}/disable")
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Property 7: Deactivate changes user status
# Validates: Requirements 4.3
# ---------------------------------------------------------------------------


@given(email=_email_strategy)
@settings(max_examples=50)
def test_property_7_disable_changes_status(email: str) -> None:
    """Property 7: For any active user, disable always sets status to disabled.

    Validates: Requirements 4.3
    """
    from httpx import ASGITransport

    email_svc = MockEmailService()
    repo = InMemoryUserRepository()
    factory = MockAdminRepositoryFactory(user_repo=repo)
    svc_factory = MockServiceFactory(email_svc=email_svc)

    try:
        user = _make_user(email, UserStatus.ACTIVE)
    except Exception:
        return

    asyncio.run(repo.save(user))
    _override_deps(factory, svc_factory)
    try:
        transport = ASGITransport(app=app)

        async def _run() -> tuple[int, str]:
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post(f"/admin/users/{user.user_id}/disable")
                return resp.status_code, resp.json().get("status", "")

        status_code, status_val = asyncio.run(_run())
        assert status_code == 200
        assert status_val == "disabled"
    finally:
        _clear_overrides()


# ---------------------------------------------------------------------------
# Property 11: Cannot disable already disabled user
# Validates: Requirements 4.5
# ---------------------------------------------------------------------------


@given(email=_email_strategy)
@settings(max_examples=50)
def test_property_11_cannot_disable_already_disabled(email: str) -> None:
    """Property 11: Disabling an already disabled user always returns 400.

    Validates: Requirements 4.5
    """
    from httpx import ASGITransport

    email_svc = MockEmailService()
    repo = InMemoryUserRepository()
    factory = MockAdminRepositoryFactory(user_repo=repo)
    svc_factory = MockServiceFactory(email_svc=email_svc)

    try:
        user = _make_user(email, UserStatus.DISABLED)
    except Exception:
        return

    asyncio.run(repo.save(user))
    _override_deps(factory, svc_factory)
    try:
        transport = ASGITransport(app=app)

        async def _run() -> int:
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post(f"/admin/users/{user.user_id}/disable")
                return resp.status_code

        status_code = asyncio.run(_run())
        assert status_code == 400
    finally:
        _clear_overrides()


# ---------------------------------------------------------------------------
# POST /admin/users/{user_id}/reactivate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reactivate_disabled_user(
    client: AsyncClient,
    mock_repo_factory: MockAdminRepositoryFactory,
    mock_email_service: MockEmailService,
) -> None:
    """POST /admin/users/{user_id}/reactivate returns 200 and sends new token."""
    user = _make_user("disabled2@example.com", UserStatus.DISABLED)
    await mock_repo_factory.users.save(user)

    response = await client.post(f"/admin/users/{user.user_id}/reactivate")
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["status"] == "active"
    assert len(mock_email_service.sent_emails) == 1


# ---------------------------------------------------------------------------
# Property 8: Reactivate restores user status
# Validates: Requirements 4.4
# ---------------------------------------------------------------------------


@given(email=_email_strategy)
@settings(max_examples=50)
def test_property_8_reactivate_restores_status(email: str) -> None:
    """Property 8: For any disabled user, reactivate sets status back to active.

    Validates: Requirements 4.4
    """
    from httpx import ASGITransport

    email_svc = MockEmailService()
    repo = InMemoryUserRepository()
    factory = MockAdminRepositoryFactory(user_repo=repo)
    svc_factory = MockServiceFactory(email_svc=email_svc)

    try:
        user = _make_user(email, UserStatus.DISABLED)
    except Exception:
        return

    asyncio.run(repo.save(user))
    _override_deps(factory, svc_factory)
    try:
        transport = ASGITransport(app=app)

        async def _run() -> tuple[int, str]:
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post(f"/admin/users/{user.user_id}/reactivate")
                return resp.status_code, resp.json().get("user", {}).get("status", "")

        status_code, status_val = asyncio.run(_run())
        assert status_code == 200
        assert status_val == "active"
    finally:
        _clear_overrides()


# ---------------------------------------------------------------------------
# DELETE /admin/users/{user_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_existing_user(
    client: AsyncClient, mock_repo_factory: MockAdminRepositoryFactory
) -> None:
    """DELETE /admin/users/{user_id} returns 204 for existing user."""
    user = _make_user("todelete@example.com", UserStatus.ACTIVE)
    await mock_repo_factory.users.save(user)

    response = await client.delete(f"/admin/users/{user.user_id}")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_already_deleted_user(
    client: AsyncClient, mock_repo_factory: MockAdminRepositoryFactory
) -> None:
    """DELETE /admin/users/{user_id} returns 400 for already deleted user."""
    user = _make_user("alreadydeleted@example.com", UserStatus.DELETED)
    await mock_repo_factory.users.save(user)

    response = await client.delete(f"/admin/users/{user.user_id}")
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Property 9: Delete marks user as deleted
# Validates: Requirements 5.4, 5.5
# ---------------------------------------------------------------------------


@given(email=_email_strategy)
@settings(max_examples=50)
def test_property_9_delete_marks_user_deleted(email: str) -> None:
    """Property 9: For any user, DELETE marks them as deleted (204 response).

    Validates: Requirements 5.4, 5.5
    """
    from httpx import ASGITransport

    email_svc = MockEmailService()
    repo = InMemoryUserRepository()
    factory = MockAdminRepositoryFactory(user_repo=repo)
    svc_factory = MockServiceFactory(email_svc=email_svc)

    try:
        user = _make_user(email, UserStatus.ACTIVE)
    except Exception:
        return

    asyncio.run(repo.save(user))
    _override_deps(factory, svc_factory)
    try:
        transport = ASGITransport(app=app)

        async def _run() -> tuple[int, str]:
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.delete(f"/admin/users/{user.user_id}")
                # Verify user is now marked deleted in the repo
                stored = await repo.get_by_id(user.user_id)
                stored_status = stored.status.value if stored else ""
                return resp.status_code, stored_status

        status_code, stored_status = asyncio.run(_run())
        assert status_code == 204
        assert stored_status == "deleted"
    finally:
        _clear_overrides()


# ---------------------------------------------------------------------------
# Property 12: Cannot delete already deleted user
# Validates: Requirements 5.6
# ---------------------------------------------------------------------------


@given(email=_email_strategy)
@settings(max_examples=50)
def test_property_12_cannot_delete_already_deleted(email: str) -> None:
    """Property 12: Deleting an already deleted user always returns 400.

    Validates: Requirements 5.6
    """
    from httpx import ASGITransport

    email_svc = MockEmailService()
    repo = InMemoryUserRepository()
    factory = MockAdminRepositoryFactory(user_repo=repo)
    svc_factory = MockServiceFactory(email_svc=email_svc)

    try:
        user = _make_user(email, UserStatus.DELETED)
    except Exception:
        return

    asyncio.run(repo.save(user))
    _override_deps(factory, svc_factory)
    try:
        transport = ASGITransport(app=app)

        async def _run() -> int:
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.delete(f"/admin/users/{user.user_id}")
                return resp.status_code

        status_code = asyncio.run(_run())
        assert status_code == 400
    finally:
        _clear_overrides()
