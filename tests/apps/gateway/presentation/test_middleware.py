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


def test_request_id_is_echoed_when_provided() -> None:
    client = TestClient(_make_echo_app())
    resp = client.get("/ping", headers={"X-Request-ID": "my-id"})
    assert resp.headers["X-Request-ID"] == "my-id"


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
