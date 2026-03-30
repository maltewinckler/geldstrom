"""Tests for middleware: exception handlers, request ID, and cache control."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI
from starlette.requests import Request
from starlette.testclient import TestClient

from gateway.application.common import (
    BankUpstreamUnavailableError,
    ForbiddenError,
    InstitutionNotFoundError,
    InternalError,
    OperationExpiredError,
    OperationNotFoundError,
    UnauthorizedError,
    UnsupportedProtocolError,
    ValidationError,
)
from gateway.presentation.http.middleware.cache_control import CacheControlMiddleware
from gateway.presentation.http.middleware.exception_handlers import (
    application_error_handler,
)
from gateway.presentation.http.middleware.rate_limit import RateLimitMiddleware
from gateway.presentation.http.middleware.request_id import RequestIDMiddleware

# ---------------------------------------------------------------------------
# exception_handlers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "exc, expected_status",
    [
        (UnauthorizedError("bad key"), 401),
        (ForbiddenError("disabled"), 403),
        (ValidationError("bad input"), 422),
        (UnsupportedProtocolError("xml?"), 422),
        (InstitutionNotFoundError("blz"), 404),
        (OperationNotFoundError("id"), 404),
        (OperationExpiredError("expired"), 404),
        (BankUpstreamUnavailableError("down"), 502),
        (InternalError("boom"), 500),
    ],
)
def test_application_error_handler_status_codes(exc, expected_status) -> None:
    request = Request({"type": "http", "method": "GET", "url": "http://test/"})
    response = asyncio.run(application_error_handler(request, exc))
    assert response.status_code == expected_status


def test_application_error_handler_body_shape() -> None:
    exc = UnauthorizedError("bad key")
    request = Request({"type": "http", "method": "GET", "url": "http://test/"})
    response = asyncio.run(application_error_handler(request, exc))
    import json

    body = json.loads(response.body)
    assert body["error"] == "unauthorized"
    assert body["message"] == "bad key"


# ---------------------------------------------------------------------------
# request_id
# ---------------------------------------------------------------------------


def _make_echo_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/ping")
    def ping():
        return {"ok": True}

    return app


def test_request_id_is_echoed_when_provided_as_uuid() -> None:
    client = TestClient(_make_echo_app())
    valid_uuid = "12345678-1234-5678-1234-567812345678"
    resp = client.get("/ping", headers={"X-Request-ID": valid_uuid})
    assert resp.headers["X-Request-ID"] == valid_uuid


def test_request_id_is_replaced_when_not_a_uuid() -> None:
    client = TestClient(_make_echo_app())
    resp = client.get("/ping", headers={"X-Request-ID": "not-a-uuid"})
    echoed = resp.headers["X-Request-ID"]
    assert echoed != "not-a-uuid"
    assert len(echoed) == 36  # freshly generated UUID


def test_request_id_is_generated_when_missing() -> None:
    client = TestClient(_make_echo_app())
    resp = client.get("/ping")
    request_id = resp.headers.get("X-Request-ID")
    assert request_id is not None
    assert len(request_id) == 36  # UUID v4


# ---------------------------------------------------------------------------
# cache_control
# ---------------------------------------------------------------------------


def _make_cache_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(CacheControlMiddleware)

    @app.get("/health/live")
    def health_live():
        return {"status": "ok"}

    @app.get("/v1/banking/accounts")
    def accounts():
        return {"accounts": []}

    return app


def test_cache_control_not_set_on_health_routes() -> None:
    client = TestClient(_make_cache_app())
    resp = client.get("/health/live")
    assert resp.headers.get("Cache-Control") != "no-store"


def test_cache_control_no_store_on_api_routes() -> None:
    client = TestClient(_make_cache_app())
    resp = client.get("/v1/banking/accounts")
    assert resp.headers["Cache-Control"] == "no-store"


# ---------------------------------------------------------------------------
# rate_limit
# ---------------------------------------------------------------------------


def _make_rate_limit_app(*, requests_per_minute: int) -> FastAPI:
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, requests_per_minute=requests_per_minute)

    @app.get("/v1/banking/accounts")
    def accounts():
        return {"ok": True}

    @app.get("/health/live")
    def health():
        return {"ok": True}

    return app


def test_rate_limit_allows_requests_within_limit() -> None:
    client = TestClient(_make_rate_limit_app(requests_per_minute=3))
    for _ in range(3):
        assert client.get("/v1/banking/accounts").status_code == 200


def test_rate_limit_blocks_request_exceeding_limit() -> None:
    client = TestClient(_make_rate_limit_app(requests_per_minute=3))
    for _ in range(3):
        client.get("/v1/banking/accounts")
    resp = client.get("/v1/banking/accounts")
    assert resp.status_code == 429
    assert resp.json() == {"detail": "Rate limit exceeded"}
    assert resp.headers["Retry-After"] == "60"


def test_rate_limit_is_per_caller_key() -> None:
    client = TestClient(_make_rate_limit_app(requests_per_minute=2))
    for _ in range(2):
        client.get("/v1/banking/accounts", headers={"Authorization": "Bearer key-a"})
    # key-a is at limit; key-b should still be allowed
    resp_a = client.get(
        "/v1/banking/accounts", headers={"Authorization": "Bearer key-a"}
    )
    resp_b = client.get(
        "/v1/banking/accounts", headers={"Authorization": "Bearer key-b"}
    )
    assert resp_a.status_code == 429
    assert resp_b.status_code == 200


def test_rate_limit_does_not_apply_to_health_routes() -> None:
    client = TestClient(_make_rate_limit_app(requests_per_minute=1))
    client.get("/v1/banking/accounts")  # exhaust the limit
    resp = client.get("/health/live")
    assert resp.status_code == 200
