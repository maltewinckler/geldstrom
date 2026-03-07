"""Unit tests for the API key routes.

Tests all 6 API key routes with TestClient and mock use cases:
- POST /admin/accounts
- GET /admin/accounts/{account_id}
- DELETE /admin/accounts/{account_id}
- POST /admin/api-keys
- DELETE /admin/api-keys/{key_id}
- POST /admin/api-keys/{key_id}/rotate
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from admin.api.api_keys import routes
from admin.api.api_keys.routes import router
from admin.api.auth import get_admin_token
from admin.api.error_handlers import register_exception_handlers
from admin.domain.api_keys.entities.account import Account
from admin.domain.api_keys.entities.api_key import ApiKey
from admin.domain.api_keys.value_objects.key_hash import KeyHash
from admin.domain.api_keys.value_objects.key_status import KeyStatus
from admin.domain.api_keys.value_objects.raw_key import RawKey
from admin.domain.api_keys.value_objects.sha256_key_hash import SHA256KeyHash
from admin.domain.exceptions import (
    AccountHasKeysError,
    AccountNotFoundError,
    ApiKeyAlreadyExistsError,
    ApiKeyAlreadyRevokedError,
    ApiKeyNotFoundError,
)


class TestApiKeyRoutes:
    """Tests for API key routes."""

    @pytest.fixture
    def mock_create_account(self) -> AsyncMock:
        """Create a mock CreateAccount use case."""
        return AsyncMock()

    @pytest.fixture
    def mock_get_account(self) -> AsyncMock:
        """Create a mock GetAccount use case."""
        return AsyncMock()

    @pytest.fixture
    def mock_delete_account(self) -> AsyncMock:
        """Create a mock DeleteAccount use case."""
        return AsyncMock()

    @pytest.fixture
    def mock_create_api_key(self) -> AsyncMock:
        """Create a mock CreateApiKey use case."""
        return AsyncMock()

    @pytest.fixture
    def mock_revoke_api_key(self) -> AsyncMock:
        """Create a mock RevokeApiKey use case."""
        return AsyncMock()

    @pytest.fixture
    def mock_rotate_api_key(self) -> AsyncMock:
        """Create a mock RotateApiKey use case."""
        return AsyncMock()

    @pytest.fixture
    def app(
        self,
        mock_create_account: AsyncMock,
        mock_get_account: AsyncMock,
        mock_delete_account: AsyncMock,
        mock_create_api_key: AsyncMock,
        mock_revoke_api_key: AsyncMock,
        mock_rotate_api_key: AsyncMock,
    ) -> FastAPI:
        """Create a test FastAPI app with mocked dependencies."""
        app = FastAPI()

        # Override dependency injection
        app.dependency_overrides[routes.get_create_account] = lambda: (
            mock_create_account
        )
        app.dependency_overrides[routes.get_get_account] = lambda: mock_get_account
        app.dependency_overrides[routes.get_delete_account] = lambda: (
            mock_delete_account
        )
        app.dependency_overrides[routes.get_create_api_key] = lambda: (
            mock_create_api_key
        )
        app.dependency_overrides[routes.get_revoke_api_key] = lambda: (
            mock_revoke_api_key
        )
        app.dependency_overrides[routes.get_rotate_api_key] = lambda: (
            mock_rotate_api_key
        )
        app.dependency_overrides[get_admin_token] = lambda: "test_token"

        app.include_router(router)
        register_exception_handlers(app)
        return app

    @pytest.fixture
    def client(self, app: FastAPI) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self) -> dict:
        """Create authorization headers."""
        return {"Authorization": "Bearer test_token"}

    # POST /admin/accounts tests
    @pytest.mark.asyncio
    async def test_create_account_success(
        self,
        client: TestClient,
        mock_create_account: AsyncMock,
        auth_headers: dict,
    ) -> None:
        """POST /admin/accounts should create an account and return 201."""
        account_id = uuid4()
        created_at = datetime.now(UTC)
        mock_create_account.execute.return_value = Account(
            id=account_id, created_at=created_at
        )

        response = client.post(
            "/admin/accounts",
            json={"account_id": str(account_id)},
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["account_id"] == str(account_id)
        assert data["api_keys"] == []

    @pytest.mark.asyncio
    async def test_create_account_unauthorized(
        self,
        client: TestClient,
    ) -> None:
        """POST /admin/accounts without auth should return 401."""
        response = client.post(
            "/admin/accounts",
            json={"account_id": str(uuid4())},
        )
        assert response.status_code == 401

    # GET /admin/accounts/{account_id} tests
    @pytest.mark.asyncio
    async def test_get_account_success(
        self,
        client: TestClient,
        mock_get_account: AsyncMock,
        auth_headers: dict,
    ) -> None:
        """GET /admin/accounts/{account_id} should return account with keys."""
        account_id = uuid4()
        created_at = datetime.now(UTC)
        account = Account(id=account_id, created_at=created_at)
        api_key = ApiKey(
            id=uuid4(),
            account_id=account_id,
            key_hash=KeyHash(value="hash"),
            sha256_key_hash=SHA256KeyHash(value="a" * 64),
            status=KeyStatus.active,
            created_at=created_at,
        )
        mock_get_account.execute.return_value = (account, [api_key])

        response = client.get(
            f"/admin/accounts/{account_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["account_id"] == str(account_id)
        assert len(data["api_keys"]) == 1
        assert data["api_keys"][0]["status"] == "active"

    @pytest.mark.asyncio
    async def test_get_account_not_found(
        self,
        client: TestClient,
        mock_get_account: AsyncMock,
        auth_headers: dict,
    ) -> None:
        """GET /admin/accounts/{account_id} should return 404 if not found."""
        account_id = uuid4()
        mock_get_account.execute.side_effect = AccountNotFoundError(str(account_id))

        response = client.get(
            f"/admin/accounts/{account_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    # DELETE /admin/accounts/{account_id} tests
    @pytest.mark.asyncio
    async def test_delete_account_success(
        self,
        client: TestClient,
        mock_delete_account: AsyncMock,
        auth_headers: dict,
    ) -> None:
        """DELETE /admin/accounts/{account_id} should return 204."""
        account_id = uuid4()
        mock_delete_account.execute.return_value = None

        response = client.delete(
            f"/admin/accounts/{account_id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_account_not_found(
        self,
        client: TestClient,
        mock_delete_account: AsyncMock,
        auth_headers: dict,
    ) -> None:
        """DELETE /admin/accounts/{account_id} should return 404 if not found."""
        account_id = uuid4()
        mock_delete_account.execute.side_effect = AccountNotFoundError(str(account_id))

        response = client.delete(
            f"/admin/accounts/{account_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_account_has_keys(
        self,
        client: TestClient,
        mock_delete_account: AsyncMock,
        auth_headers: dict,
    ) -> None:
        """DELETE /admin/accounts/{account_id} should return 409 if has keys."""
        account_id = uuid4()
        mock_delete_account.execute.side_effect = AccountHasKeysError(str(account_id))

        response = client.delete(
            f"/admin/accounts/{account_id}",
            headers=auth_headers,
        )

        assert response.status_code == 409

    # POST /admin/api-keys tests
    @pytest.mark.asyncio
    async def test_create_api_key_success(
        self,
        client: TestClient,
        mock_create_api_key: AsyncMock,
        auth_headers: dict,
    ) -> None:
        """POST /admin/api-keys should create a key and return 201."""
        account_id = uuid4()
        key_id = uuid4()
        raw_key = RawKey(value=SecretStr("a" * 64))
        mock_create_api_key.execute.return_value = (key_id, raw_key)

        response = client.post(
            "/admin/api-keys",
            json={"account_id": str(account_id)},
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["key_id"] == str(key_id)
        assert data["raw_key"] == "a" * 64

    @pytest.mark.asyncio
    async def test_create_api_key_account_not_found(
        self,
        client: TestClient,
        mock_create_api_key: AsyncMock,
        auth_headers: dict,
    ) -> None:
        """POST /admin/api-keys should return 404 if account not found."""
        account_id = uuid4()
        mock_create_api_key.execute.side_effect = AccountNotFoundError(str(account_id))

        response = client.post(
            "/admin/api-keys",
            json={"account_id": str(account_id)},
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_api_key_already_exists(
        self,
        client: TestClient,
        mock_create_api_key: AsyncMock,
        auth_headers: dict,
    ) -> None:
        """POST /admin/api-keys should return 409 if key already exists."""
        account_id = uuid4()
        mock_create_api_key.execute.side_effect = ApiKeyAlreadyExistsError(
            str(account_id)
        )

        response = client.post(
            "/admin/api-keys",
            json={"account_id": str(account_id)},
            headers=auth_headers,
        )

        assert response.status_code == 409

    # DELETE /admin/api-keys/{key_id} tests
    @pytest.mark.asyncio
    async def test_revoke_api_key_success(
        self,
        client: TestClient,
        mock_revoke_api_key: AsyncMock,
        auth_headers: dict,
    ) -> None:
        """DELETE /admin/api-keys/{key_id} should return 204."""
        key_id = uuid4()
        mock_revoke_api_key.execute.return_value = None

        response = client.delete(
            f"/admin/api-keys/{key_id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_revoke_api_key_not_found(
        self,
        client: TestClient,
        mock_revoke_api_key: AsyncMock,
        auth_headers: dict,
    ) -> None:
        """DELETE /admin/api-keys/{key_id} should return 404 if not found."""
        key_id = uuid4()
        mock_revoke_api_key.execute.side_effect = ApiKeyNotFoundError(str(key_id))

        response = client.delete(
            f"/admin/api-keys/{key_id}",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_revoke_api_key_already_revoked(
        self,
        client: TestClient,
        mock_revoke_api_key: AsyncMock,
        auth_headers: dict,
    ) -> None:
        """DELETE /admin/api-keys/{key_id} should return 409 if already revoked."""
        key_id = uuid4()
        mock_revoke_api_key.execute.side_effect = ApiKeyAlreadyRevokedError(str(key_id))

        response = client.delete(
            f"/admin/api-keys/{key_id}",
            headers=auth_headers,
        )

        assert response.status_code == 409

    # POST /admin/api-keys/{key_id}/rotate tests
    @pytest.mark.asyncio
    async def test_rotate_api_key_success(
        self,
        client: TestClient,
        mock_rotate_api_key: AsyncMock,
        auth_headers: dict,
    ) -> None:
        """POST /admin/api-keys/{key_id}/rotate should return new key."""
        key_id = uuid4()
        new_key_id = uuid4()
        raw_key = RawKey(value=SecretStr("b" * 64))
        mock_rotate_api_key.execute.return_value = (new_key_id, raw_key)

        response = client.post(
            f"/admin/api-keys/{key_id}/rotate",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["key_id"] == str(new_key_id)
        assert data["raw_key"] == "b" * 64

    @pytest.mark.asyncio
    async def test_rotate_api_key_not_found(
        self,
        client: TestClient,
        mock_rotate_api_key: AsyncMock,
        auth_headers: dict,
    ) -> None:
        """POST /admin/api-keys/{key_id}/rotate should return 404 if not found."""
        key_id = uuid4()
        mock_rotate_api_key.execute.side_effect = ApiKeyNotFoundError(str(key_id))

        response = client.post(
            f"/admin/api-keys/{key_id}/rotate",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_rotate_api_key_already_revoked(
        self,
        client: TestClient,
        mock_rotate_api_key: AsyncMock,
        auth_headers: dict,
    ) -> None:
        """POST /admin/api-keys/{key_id}/rotate should return 409 if revoked."""
        key_id = uuid4()
        mock_rotate_api_key.execute.side_effect = ApiKeyAlreadyRevokedError(str(key_id))

        response = client.post(
            f"/admin/api-keys/{key_id}/rotate",
            headers=auth_headers,
        )

        assert response.status_code == 409
