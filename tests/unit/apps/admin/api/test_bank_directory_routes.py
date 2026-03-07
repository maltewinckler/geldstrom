"""Unit tests for the bank directory routes.

Tests all 5 bank directory routes with TestClient and mock use cases:
- POST /admin/bank-endpoints
- GET /admin/bank-endpoints
- GET /admin/bank-endpoints/{bank_code}
- PUT /admin/bank-endpoints/{bank_code}
- DELETE /admin/bank-endpoints/{bank_code}
"""

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from admin.api.auth import get_admin_token
from admin.api.bank_directory import routes
from admin.api.bank_directory.routes import router
from admin.api.error_handlers import register_exception_handlers
from admin.domain.bank_directory.entities.bank_endpoint import BankEndpoint
from admin.domain.bank_directory.value_objects.banking_protocol import BankingProtocol
from admin.domain.bank_directory.value_objects.protocol_config import FinTSConfig
from admin.domain.exceptions import (
    BankEndpointAlreadyExistsError,
    BankEndpointNotFoundError,
)


class TestBankDirectoryRoutes:
    """Tests for bank directory routes."""

    @pytest.fixture
    def mock_create_bank_endpoint(self) -> AsyncMock:
        """Create a mock CreateBankEndpoint use case."""
        return AsyncMock()

    @pytest.fixture
    def mock_list_bank_endpoints(self) -> AsyncMock:
        """Create a mock ListBankEndpoints use case."""
        return AsyncMock()

    @pytest.fixture
    def mock_get_bank_endpoint(self) -> AsyncMock:
        """Create a mock GetBankEndpoint use case."""
        return AsyncMock()

    @pytest.fixture
    def mock_update_bank_endpoint(self) -> AsyncMock:
        """Create a mock UpdateBankEndpoint use case."""
        return AsyncMock()

    @pytest.fixture
    def mock_delete_bank_endpoint(self) -> AsyncMock:
        """Create a mock DeleteBankEndpoint use case."""
        return AsyncMock()

    @pytest.fixture
    def app(
        self,
        mock_create_bank_endpoint: AsyncMock,
        mock_list_bank_endpoints: AsyncMock,
        mock_get_bank_endpoint: AsyncMock,
        mock_update_bank_endpoint: AsyncMock,
        mock_delete_bank_endpoint: AsyncMock,
    ) -> FastAPI:
        """Create a test FastAPI app with mocked dependencies."""
        app = FastAPI()

        # Override dependency injection
        app.dependency_overrides[routes.get_create_bank_endpoint] = lambda: (
            mock_create_bank_endpoint
        )
        app.dependency_overrides[routes.get_list_bank_endpoints] = lambda: (
            mock_list_bank_endpoints
        )
        app.dependency_overrides[routes.get_get_bank_endpoint] = lambda: (
            mock_get_bank_endpoint
        )
        app.dependency_overrides[routes.get_update_bank_endpoint] = lambda: (
            mock_update_bank_endpoint
        )
        app.dependency_overrides[routes.get_delete_bank_endpoint] = lambda: (
            mock_delete_bank_endpoint
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

    @pytest.fixture
    def bank_endpoint(self) -> BankEndpoint:
        """Create a sample BankEndpoint."""
        return BankEndpoint(
            bank_code="TEST001",
            protocol=BankingProtocol.fints,
            server_url="https://fints.example.com",
            protocol_config=FinTSConfig(
                product_id=SecretStr("test_product_id"),
                product_version="1.0.0",
                country_code="DE",
            ),
            metadata={"key": "value"},
        )

    @pytest.fixture
    def endpoint_request(self) -> dict:
        """Create a sample endpoint request body."""
        return {
            "bank_code": "TEST001",
            "protocol": "fints",
            "server_url": "https://fints.example.com",
            "protocol_config": {
                "product_id": "test_product_id",
                "product_version": "1.0.0",
                "country_code": "DE",
            },
            "metadata": {"key": "value"},
        }

    # POST /admin/bank-endpoints tests
    @pytest.mark.asyncio
    async def test_create_bank_endpoint_success(
        self,
        client: TestClient,
        mock_create_bank_endpoint: AsyncMock,
        auth_headers: dict,
        endpoint_request: dict,
    ) -> None:
        """POST /admin/bank-endpoints should create endpoint and return 201."""
        mock_create_bank_endpoint.execute.return_value = None

        response = client.post(
            "/admin/bank-endpoints",
            json=endpoint_request,
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["bank_code"] == "TEST001"
        assert data["protocol"] == "fints"
        assert data["server_url"] == "https://fints.example.com/"
        # protocol_config should be redacted (not in response)
        assert "protocol_config" not in data

    @pytest.mark.asyncio
    async def test_create_bank_endpoint_already_exists(
        self,
        client: TestClient,
        mock_create_bank_endpoint: AsyncMock,
        auth_headers: dict,
        endpoint_request: dict,
    ) -> None:
        """POST /admin/bank-endpoints should return 409 if already exists."""
        mock_create_bank_endpoint.execute.side_effect = BankEndpointAlreadyExistsError(
            "TEST001"
        )

        response = client.post(
            "/admin/bank-endpoints",
            json=endpoint_request,
            headers=auth_headers,
        )

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_create_bank_endpoint_unauthorized(
        self,
        client: TestClient,
        endpoint_request: dict,
    ) -> None:
        """POST /admin/bank-endpoints without auth should return 401."""
        response = client.post(
            "/admin/bank-endpoints",
            json=endpoint_request,
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_bank_endpoint_invalid_bank_code(
        self,
        client: TestClient,
        auth_headers: dict,
        endpoint_request: dict,
    ) -> None:
        """POST /admin/bank-endpoints with invalid bank_code should return 422."""
        endpoint_request["bank_code"] = ""  # Empty bank_code

        response = client.post(
            "/admin/bank-endpoints",
            json=endpoint_request,
            headers=auth_headers,
        )

        assert response.status_code == 422

    # GET /admin/bank-endpoints tests
    @pytest.mark.asyncio
    async def test_list_bank_endpoints_success(
        self,
        client: TestClient,
        mock_list_bank_endpoints: AsyncMock,
        auth_headers: dict,
        bank_endpoint: BankEndpoint,
    ) -> None:
        """GET /admin/bank-endpoints should return list of endpoints."""
        mock_list_bank_endpoints.execute.return_value = [bank_endpoint]

        response = client.get(
            "/admin/bank-endpoints",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["bank_code"] == "TEST001"

    @pytest.mark.asyncio
    async def test_list_bank_endpoints_empty(
        self,
        client: TestClient,
        mock_list_bank_endpoints: AsyncMock,
        auth_headers: dict,
    ) -> None:
        """GET /admin/bank-endpoints should return empty list if none exist."""
        mock_list_bank_endpoints.execute.return_value = []

        response = client.get(
            "/admin/bank-endpoints",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json() == []

    # GET /admin/bank-endpoints/{bank_code} tests
    @pytest.mark.asyncio
    async def test_get_bank_endpoint_success(
        self,
        client: TestClient,
        mock_get_bank_endpoint: AsyncMock,
        auth_headers: dict,
        bank_endpoint: BankEndpoint,
    ) -> None:
        """GET /admin/bank-endpoints/{bank_code} should return endpoint."""
        mock_get_bank_endpoint.execute.return_value = bank_endpoint

        response = client.get(
            "/admin/bank-endpoints/TEST001",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["bank_code"] == "TEST001"
        assert data["protocol"] == "fints"

    @pytest.mark.asyncio
    async def test_get_bank_endpoint_not_found(
        self,
        client: TestClient,
        mock_get_bank_endpoint: AsyncMock,
        auth_headers: dict,
    ) -> None:
        """GET /admin/bank-endpoints/{bank_code} should return 404 if not found."""
        mock_get_bank_endpoint.execute.side_effect = BankEndpointNotFoundError(
            "NONEXISTENT"
        )

        response = client.get(
            "/admin/bank-endpoints/NONEXISTENT",
            headers=auth_headers,
        )

        assert response.status_code == 404

    # PUT /admin/bank-endpoints/{bank_code} tests
    @pytest.mark.asyncio
    async def test_update_bank_endpoint_success(
        self,
        client: TestClient,
        mock_update_bank_endpoint: AsyncMock,
        auth_headers: dict,
        endpoint_request: dict,
    ) -> None:
        """PUT /admin/bank-endpoints/{bank_code} should update and return 200."""
        mock_update_bank_endpoint.execute.return_value = None

        response = client.put(
            "/admin/bank-endpoints/TEST001",
            json=endpoint_request,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["bank_code"] == "TEST001"

    @pytest.mark.asyncio
    async def test_update_bank_endpoint_not_found(
        self,
        client: TestClient,
        mock_update_bank_endpoint: AsyncMock,
        auth_headers: dict,
        endpoint_request: dict,
    ) -> None:
        """PUT /admin/bank-endpoints/{bank_code} should return 404 if not found."""
        mock_update_bank_endpoint.execute.side_effect = BankEndpointNotFoundError(
            "TEST001"
        )

        response = client.put(
            "/admin/bank-endpoints/TEST001",
            json=endpoint_request,
            headers=auth_headers,
        )

        assert response.status_code == 404

    # DELETE /admin/bank-endpoints/{bank_code} tests
    @pytest.mark.asyncio
    async def test_delete_bank_endpoint_success(
        self,
        client: TestClient,
        mock_delete_bank_endpoint: AsyncMock,
        auth_headers: dict,
    ) -> None:
        """DELETE /admin/bank-endpoints/{bank_code} should return 204."""
        mock_delete_bank_endpoint.execute.return_value = None

        response = client.delete(
            "/admin/bank-endpoints/TEST001",
            headers=auth_headers,
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_bank_endpoint_not_found(
        self,
        client: TestClient,
        mock_delete_bank_endpoint: AsyncMock,
        auth_headers: dict,
    ) -> None:
        """DELETE /admin/bank-endpoints/{bank_code} should return 404 if not found."""
        mock_delete_bank_endpoint.execute.side_effect = BankEndpointNotFoundError(
            "TEST001"
        )

        response = client.delete(
            "/admin/bank-endpoints/TEST001",
            headers=auth_headers,
        )

        assert response.status_code == 404

    # Response redaction tests
    @pytest.mark.asyncio
    async def test_response_does_not_include_protocol_config(
        self,
        client: TestClient,
        mock_get_bank_endpoint: AsyncMock,
        auth_headers: dict,
        bank_endpoint: BankEndpoint,
    ) -> None:
        """Responses should not include protocol_config (secrets redacted)."""
        mock_get_bank_endpoint.execute.return_value = bank_endpoint

        response = client.get(
            "/admin/bank-endpoints/TEST001",
            headers=auth_headers,
        )

        data = response.json()
        assert "protocol_config" not in data
        assert "product_id" not in data
