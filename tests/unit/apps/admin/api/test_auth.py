"""Unit tests for the verify_token dependency.

Tests:
- Valid token
- Invalid token
- Missing header
"""

import os
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from admin.api.auth import get_admin_token, verify_token


class TestGetAdminToken:
    """Tests for get_admin_token function."""

    def test_returns_token_from_env(self) -> None:
        """get_admin_token should return the ADMIN_API_TOKEN env var."""
        with patch.dict(os.environ, {"ADMIN_API_TOKEN": "test_token_123"}):
            token = get_admin_token()
            assert token == "test_token_123"

    def test_raises_key_error_when_not_set(self) -> None:
        """get_admin_token should raise KeyError when env var not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove ADMIN_API_TOKEN if it exists
            os.environ.pop("ADMIN_API_TOKEN", None)
            with pytest.raises(KeyError):
                get_admin_token()


class TestVerifyToken:
    """Tests for verify_token dependency."""

    @pytest.fixture
    def app(self) -> FastAPI:
        """Create a test FastAPI app with a protected endpoint."""
        app = FastAPI()

        @app.get("/protected")
        async def protected_endpoint(
            _: None = pytest.importorskip("fastapi").Depends(verify_token),
        ):
            return {"message": "success"}

        return app

    @pytest.fixture
    def client(self, app: FastAPI) -> TestClient:
        """Create a test client."""
        return TestClient(app)

    def test_valid_token_allows_access(self, client: TestClient) -> None:
        """A valid token should allow access to protected endpoints."""
        with patch.dict(os.environ, {"ADMIN_API_TOKEN": "valid_token"}):
            response = client.get(
                "/protected",
                headers={"Authorization": "Bearer valid_token"},
            )
            assert response.status_code == 200
            assert response.json() == {"message": "success"}

    def test_invalid_token_returns_401(self, client: TestClient) -> None:
        """An invalid token should return 401."""
        with patch.dict(os.environ, {"ADMIN_API_TOKEN": "valid_token"}):
            response = client.get(
                "/protected",
                headers={"Authorization": "Bearer invalid_token"},
            )
            assert response.status_code == 401
            assert response.json()["detail"] == "Invalid token"

    def test_missing_header_returns_401(self, client: TestClient) -> None:
        """A missing Authorization header should return 401."""
        with patch.dict(os.environ, {"ADMIN_API_TOKEN": "valid_token"}):
            response = client.get("/protected")
            # HTTPBearer returns 401 for missing credentials
            assert response.status_code == 401

    def test_malformed_header_returns_401(self, client: TestClient) -> None:
        """A malformed Authorization header should return 401."""
        with patch.dict(os.environ, {"ADMIN_API_TOKEN": "valid_token"}):
            response = client.get(
                "/protected",
                headers={"Authorization": "NotBearer token"},
            )
            # HTTPBearer returns 401 for invalid scheme
            assert response.status_code == 401

    def test_empty_bearer_token_returns_401(self, client: TestClient) -> None:
        """An empty bearer token should return 401."""
        with patch.dict(os.environ, {"ADMIN_API_TOKEN": "valid_token"}):
            response = client.get(
                "/protected",
                headers={"Authorization": "Bearer "},
            )
            # Empty token doesn't match, so 401
            assert response.status_code == 401
