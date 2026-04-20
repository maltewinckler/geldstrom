"""Pytest configuration and shared fixtures for gateway-admin-ui tests."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from hypothesis import HealthCheck, settings

from gateway_admin.domain.entities.users import User
from gateway_admin.domain.repositories.user_repository import UserPage, UserQuery
from gateway_admin.domain.value_objects.user import ApiKeyHash, Email, UserId
from gateway_admin.infrastructure.services.email_service import MockEmailService
from gateway_admin.presentation.api.dependencies import (
    get_repo_factory,
    get_service_factory,
)
from gateway_admin.presentation.api.main import app

settings.register_profile(
    "test",
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    max_examples=50,
)
settings.load_profile("test")


# ---------------------------------------------------------------------------
# In-memory stubs
# ---------------------------------------------------------------------------


class InMemoryUserRepository:
    """Dict-backed user repository for tests (no database required)."""

    def __init__(self) -> None:
        self._store: dict[str, User] = {}

    async def get_by_id(self, user_id: UserId) -> User | None:
        return self._store.get(str(user_id))

    async def get_by_email(self, email: Email) -> User | None:
        for user in self._store.values():
            if user.email.value == email.value:
                return user
        return None

    async def save(self, user: User) -> None:
        self._store[str(user.user_id)] = user

    async def query(self, q: UserQuery) -> UserPage:
        users = list(self._store.values())
        if q.email_contains is not None:
            users = [
                u for u in users if q.email_contains.lower() in u.email.value.lower()
            ]
        if q.status is not None:
            users = [u for u in users if u.status == q.status]
        users.sort(key=lambda u: u.email.value)
        total = len(users)
        offset = (q.page - 1) * q.page_size
        return UserPage(
            users=users[offset : offset + q.page_size],
            total=total,
            page=q.page,
            page_size=q.page_size,
        )

    async def list_all(self) -> list[User]:
        return list(self._store.values())

    async def query(self, q) -> object:
        from gateway_admin.domain.repositories.user_repository import UserPage

        users = list(self._store.values())
        if q.email_contains:
            users = [
                u for u in users if q.email_contains.lower() in u.email.value.lower()
            ]
        if q.status is not None:
            users = [u for u in users if u.status == q.status]
        users.sort(key=lambda u: u.email.value)
        total = len(users)
        start = (q.page - 1) * q.page_size
        end = start + q.page_size
        return UserPage(
            users=users[start:end], total=total, page=q.page, page_size=q.page_size
        )


class NoOpGatewayNotificationService:
    """No-op gateway notification service for tests."""

    async def notify_user_updated(self, user_id: str) -> None:
        pass

    async def notify_institute_catalog_replaced(self) -> None:
        pass

    async def notify_product_registration_updated(self) -> None:
        pass


class SimpleApiKeyService:
    def generate(self, consumer_id: str) -> str:
        prefix = consumer_id.replace("-", "")[:8]
        return f"{prefix}.{secrets.token_urlsafe(16)}"

    def hash(self, raw_key: str) -> ApiKeyHash:
        import hashlib

        digest = hashlib.sha256(raw_key.encode()).hexdigest()
        return ApiKeyHash(f"$sha256${digest}")


class SimpleIdProvider:
    def new_operation_id(self) -> str:
        return str(uuid4())

    def now(self) -> datetime:
        return datetime.now(UTC)


class NoOpAuditRepository:
    """No-op audit repository for tests — discards all events."""

    async def append(self, event) -> None:
        pass


class MockAdminRepositoryFactory:
    """In-memory AdminRepositoryFactory for tests — repositories + settings only."""

    def __init__(self, user_repo: InMemoryUserRepository) -> None:
        self._user_repo = user_repo
        self._settings = MagicMock()
        self._settings.admin_argon2_time_cost = 1
        self._settings.admin_argon2_memory_cost = 8192
        self._settings.admin_argon2_parallelism = 1
        self._audit = NoOpAuditRepository()

    @property
    def settings(self):
        return self._settings

    @property
    def users(self) -> InMemoryUserRepository:
        return self._user_repo

    @property
    def institutes(self):  # type: ignore[override]
        raise NotImplementedError("Not needed in user-focused tests")

    @property
    def product_registration(self):  # type: ignore[override]
        raise NotImplementedError("Not needed in user-focused tests")

    @property
    def audit(self) -> NoOpAuditRepository:
        return self._audit


class MockServiceFactory:
    """In-memory ServiceFactory for tests."""

    def __init__(self, email_svc: MockEmailService) -> None:
        self._gateway = NoOpGatewayNotificationService()
        self._email_service = email_svc
        self._api_key_service = SimpleApiKeyService()
        self._id_provider = SimpleIdProvider()

    @property
    def gateway_notifications(self) -> NoOpGatewayNotificationService:
        return self._gateway

    @property
    def email_service(self) -> MockEmailService:
        return self._email_service

    @property
    def api_key_service(self) -> SimpleApiKeyService:
        return self._api_key_service

    @property
    def id_provider(self) -> SimpleIdProvider:
        return self._id_provider

    @property
    def csv_reader(self):  # type: ignore[override]
        raise NotImplementedError("Not needed in user-focused tests")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_email_service() -> MockEmailService:
    return MockEmailService()


@pytest.fixture
def user_repo() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def mock_repo_factory(user_repo: InMemoryUserRepository) -> MockAdminRepositoryFactory:
    return MockAdminRepositoryFactory(user_repo=user_repo)


@pytest.fixture
def mock_service_factory(mock_email_service: MockEmailService) -> MockServiceFactory:
    return MockServiceFactory(email_svc=mock_email_service)


@pytest_asyncio.fixture
async def client(
    mock_repo_factory: MockAdminRepositoryFactory,
    mock_service_factory: MockServiceFactory,
) -> AsyncClient:
    """Async HTTP test client with both factories overridden."""
    app.dependency_overrides[get_repo_factory] = lambda: mock_repo_factory
    app.dependency_overrides[get_service_factory] = lambda: mock_service_factory
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
