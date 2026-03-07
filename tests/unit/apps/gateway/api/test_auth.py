"""Unit tests for the API key authentication dependency.

Validates Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6.
"""

from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI, Request
from httpx import ASGITransport, AsyncClient

from gateway.api.auth import create_auth_dependency
from gateway.domain.session.value_objects.audit import ApiKeyValidationResult
from gateway.infrastructure.session.api_key_validator import ApiKeyValidationError

# -------------------------------------------------------------------
# Fake validator for testing
# -------------------------------------------------------------------


class FakeValidator:
    """Configurable fake ApiKeyValidator for unit tests."""

    def __init__(
        self,
        *,
        result: ApiKeyValidationResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.last_key: str | None = None

    async def validate(self, api_key: str) -> ApiKeyValidationResult:
        self.last_key = api_key
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

_VALID_RESULT = ApiKeyValidationResult(
    is_valid=True, account_id="acct-42", metadata=None
)
_INVALID_RESULT = ApiKeyValidationResult(is_valid=False, account_id=None, metadata=None)


def _make_app(validator: FakeValidator) -> FastAPI:
    """Build a minimal FastAPI app wired with the auth dependency."""
    app = FastAPI()
    require_api_key = create_auth_dependency(validator)

    @app.get("/v1/protected")
    async def protected(account_id: str = Depends(require_api_key)):
        return {"account_id": account_id}

    @app.get("/health")
    async def health(account_id: str = Depends(require_api_key)):
        return {"status": "ok"}

    @app.get("/v1/system/version")
    async def version(account_id: str = Depends(require_api_key)):
        return {"git_commit_hash": "abc", "docker_image_sha256": "def"}

    return app


def _client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# -------------------------------------------------------------------
# Requirement 4.2 — Missing X-API-Key → 401
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_api_key_returns_401() -> None:
    """Requests without X-API-Key header must receive HTTP 401."""
    validator = FakeValidator(result=_VALID_RESULT)
    app = _make_app(validator)
    async with _client(app) as client:
        resp = await client.get("/v1/protected")
    assert resp.status_code == 401


# -------------------------------------------------------------------
# Requirement 4.5 — Invalid key → 403
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_api_key_returns_403() -> None:
    """Requests with an invalid API key must receive HTTP 403."""
    validator = FakeValidator(result=_INVALID_RESULT)
    app = _make_app(validator)
    async with _client(app) as client:
        resp = await client.get("/v1/protected", headers={"X-API-Key": "bad-key"})
    assert resp.status_code == 403


# -------------------------------------------------------------------
# Requirement 4.6 — Validator error → 503
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validator_error_returns_503() -> None:
    """When the validator backend is unavailable, return HTTP 503."""
    validator = FakeValidator(error=ApiKeyValidationError("gRPC down"))
    app = _make_app(validator)
    async with _client(app) as client:
        resp = await client.get("/v1/protected", headers={"X-API-Key": "some-key"})
    assert resp.status_code == 503


# -------------------------------------------------------------------
# Requirement 4.4 — Valid key propagates account_id
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_valid_key_propagates_account_id() -> None:
    """A valid API key should make account_id available downstream."""
    validator = FakeValidator(result=_VALID_RESULT)
    app = _make_app(validator)
    async with _client(app) as client:
        resp = await client.get("/v1/protected", headers={"X-API-Key": "good-key"})
    assert resp.status_code == 200
    assert resp.json()["account_id"] == "acct-42"


# -------------------------------------------------------------------
# Requirement 4.4 — account_id injected into request.state
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_valid_key_sets_request_state_account_id() -> None:
    """The dependency must set request.state.account_id for downstream use."""
    captured: dict = {}
    validator = FakeValidator(result=_VALID_RESULT)
    app = FastAPI()
    require_api_key = create_auth_dependency(validator)

    @app.get("/v1/check")
    async def check(request: Request, _: str = Depends(require_api_key)):
        captured["account_id"] = request.state.account_id
        return {"ok": True}

    async with _client(app) as client:
        resp = await client.get("/v1/check", headers={"X-API-Key": "good-key"})
    assert resp.status_code == 200
    assert captured["account_id"] == "acct-42"


# -------------------------------------------------------------------
# Requirement 4.3 — Validator is called with the key value
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validator_receives_raw_key() -> None:
    """The dependency must pass the raw X-API-Key value to the validator."""
    validator = FakeValidator(result=_VALID_RESULT)
    app = _make_app(validator)
    async with _client(app) as client:
        await client.get("/v1/protected", headers={"X-API-Key": "my-secret-key"})
    assert validator.last_key == "my-secret-key"


# -------------------------------------------------------------------
# Requirements 7.2, 9.2 — Public paths skip auth
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_skips_auth() -> None:
    """The /health endpoint must not require an API key."""
    validator = FakeValidator(result=_VALID_RESULT)
    app = _make_app(validator)
    async with _client(app) as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert validator.last_key is None  # validator was never called


@pytest.mark.asyncio
async def test_version_skips_auth() -> None:
    """The /v1/system/version endpoint must not require an API key."""
    validator = FakeValidator(result=_VALID_RESULT)
    app = _make_app(validator)
    async with _client(app) as client:
        resp = await client.get("/v1/system/version")
    assert resp.status_code == 200
    assert validator.last_key is None  # validator was never called
