"""Unit tests for LogScrubberMiddleware.

Validates Requirements 5.3, 5.4, 5.5.
"""

import json
import logging

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient

from gateway.api.middleware import LogScrubberMiddleware


def _make_app() -> FastAPI:
    """Minimal FastAPI app with LogScrubberMiddleware attached."""
    _app = FastAPI()
    _app.add_middleware(LogScrubberMiddleware)

    @_app.post("/echo")
    async def echo():
        return {"ok": True}

    @_app.get("/ping")
    async def ping():
        return {"pong": True}

    return _app


def _make_client(app: FastAPI) -> AsyncClient:
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# -------------------------------------------------------------------
# Requirement 5.3 — X-API-Key replaced with [REDACTED] in logs
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_log_scrubber_redacts_api_key_header(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The middleware must replace X-API-Key with [REDACTED] in log output."""
    app = _make_app()
    async with _make_client(app) as client:
        with caplog.at_level(logging.DEBUG, logger="gateway.api.middleware"):
            resp = await client.get(
                "/ping", headers={"X-API-Key": "super-secret-key-123"}
            )

    assert resp.status_code == 200

    records = [r for r in caplog.records if r.name == "gateway.api.middleware"]
    assert len(records) == 1
    log_headers = records[0].__dict__["headers"]
    assert log_headers["x-api-key"] == "[REDACTED]"


# -------------------------------------------------------------------
# Requirement 5.4 — Original request is not modified
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_log_scrubber_preserves_original_request() -> None:
    """The original request passed to the handler must retain the real key."""
    captured_header: dict = {}

    app = FastAPI()
    app.add_middleware(LogScrubberMiddleware)

    @app.get("/capture")
    async def capture(request: Request):
        captured_header["x-api-key"] = request.headers.get("x-api-key")
        return {"ok": True}

    async with _make_client(app) as client:
        resp = await client.get("/capture", headers={"X-API-Key": "my-real-key"})

    assert resp.status_code == 200
    assert captured_header["x-api-key"] == "my-real-key"


# -------------------------------------------------------------------
# Requirement 5.5 — Unparseable body logged as [UNPARSEABLE]
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_log_scrubber_unparseable_body(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Non-JSON bodies must be logged as [UNPARSEABLE]."""
    app = _make_app()
    async with _make_client(app) as client:
        with caplog.at_level(logging.DEBUG, logger="gateway.api.middleware"):
            await client.post(
                "/echo",
                content=b"this is not json {{{",
                headers={"Content-Type": "application/json"},
            )

    records = [r for r in caplog.records if r.name == "gateway.api.middleware"]
    assert len(records) == 1
    assert records[0].__dict__["body"] == "[UNPARSEABLE]"


@pytest.mark.asyncio
async def test_log_scrubber_parseable_body(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Valid JSON bodies must be logged as parsed objects (not [UNPARSEABLE])."""
    payload = {"key": "value", "num": 42}
    app = _make_app()
    async with _make_client(app) as client:
        with caplog.at_level(logging.DEBUG, logger="gateway.api.middleware"):
            await client.post(
                "/echo",
                content=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
            )

    records = [r for r in caplog.records if r.name == "gateway.api.middleware"]
    assert len(records) == 1
    assert records[0].__dict__["body"] == payload


@pytest.mark.asyncio
async def test_log_scrubber_empty_body(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Empty bodies should be logged as None, not [UNPARSEABLE]."""
    app = _make_app()
    async with _make_client(app) as client:
        with caplog.at_level(logging.DEBUG, logger="gateway.api.middleware"):
            await client.get("/ping")

    records = [r for r in caplog.records if r.name == "gateway.api.middleware"]
    assert len(records) == 1
    assert records[0].__dict__["body"] is None
