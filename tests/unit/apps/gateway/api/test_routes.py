"""Unit tests for Gateway API route handlers.

Tests the ``create_router()`` factory and its two endpoints:
- POST /v1/transactions/fetch (initial + resume flows, error mapping)
- GET  /v1/system/version (provenance, env-var fallback)

Validates Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 7.1, 7.2, 7.3
"""

from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from gateway.api.routes import create_router
from gateway.domain.banking.value_objects.connection import BankingProtocol
from gateway.domain.banking.value_objects.transaction import TransactionData
from gateway.domain.exceptions import (
    BankConnectionError,
    BankNotSupportedError,
    SessionNotFoundError,
    TANRejectedError,
    UnsupportedProtocolError,
)
from gateway.domain.session.value_objects.fetch_result import (
    ChallengeInfo,
    FetchResult,
    FetchStatus,
)


def _make_success_result() -> FetchResult:
    return FetchResult(
        status=FetchStatus.SUCCESS,
        transactions=[
            TransactionData(
                entry_id="tx-1",
                booking_date=date(2024, 1, 15),
                value_date=date(2024, 1, 15),
                amount=Decimal("-42.50"),
                currency="EUR",
                purpose="Coffee supplies",
                counterpart_name="Bean Co",
                counterpart_iban="DE89370400440532013000",
            ),
        ],
    )


def _make_challenge_result() -> FetchResult:
    return FetchResult(
        status=FetchStatus.CHALLENGE_REQUIRED,
        challenge=ChallengeInfo(
            session_id="abc123", type="photoTAN", media_data=b"\x89PNG"
        ),
    )


def _initial_body() -> dict[str, Any]:
    return {
        "bank_connection": {
            "protocol": "fints",
            "bank_code": "12345678",
            "username": "testuser",
            "pin": "testpin",
        },
        "iban": "DE89370400440532013000",
        "date_range": {"start": "2024-01-01", "end": "2024-01-31"},
    }


def _resume_body() -> dict[str, Any]:
    return {"session_id": "sess-abc", "tan_response": "123456"}


def _build_app(use_case: Any = None, audit_publisher: Any = None) -> FastAPI:
    uc = use_case or AsyncMock()
    ap = audit_publisher or AsyncMock()

    async def fake_require_api_key() -> str:
        return "acct-test"

    app = FastAPI()
    router = create_router(uc, ap, fake_require_api_key)
    app.include_router(router)
    return app


def _client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_initial_fetch_success() -> None:
    uc = AsyncMock()
    uc.execute_initial.return_value = _make_success_result()
    app = _build_app(use_case=uc)
    async with _client(app) as client:
        resp = await client.post("/v1/transactions/fetch", json=_initial_body())
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert len(data["transactions"]) == 1
    assert data["transactions"][0]["entry_id"] == "tx-1"


@pytest.mark.asyncio
async def test_initial_fetch_challenge() -> None:
    uc = AsyncMock()
    uc.execute_initial.return_value = _make_challenge_result()
    app = _build_app(use_case=uc)
    async with _client(app) as client:
        resp = await client.post("/v1/transactions/fetch", json=_initial_body())
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "challenge_required"
    assert data["challenge"]["session_id"] == "abc123"


@pytest.mark.asyncio
async def test_resume_fetch_success() -> None:
    uc = AsyncMock()
    uc.execute_resume.return_value = _make_success_result()
    app = _build_app(use_case=uc)
    async with _client(app) as client:
        resp = await client.post("/v1/transactions/fetch", json=_resume_body())
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    uc.execute_resume.assert_awaited_once_with("sess-abc", "123456")


@pytest.mark.asyncio
async def test_session_not_found_returns_404() -> None:
    uc = AsyncMock()
    uc.execute_resume.side_effect = SessionNotFoundError("sess-expired")
    app = _build_app(use_case=uc)
    async with _client(app) as client:
        resp = await client.post("/v1/transactions/fetch", json=_resume_body())
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "SESSION_NOT_FOUND"


@pytest.mark.asyncio
async def test_unsupported_protocol_returns_422() -> None:
    uc = AsyncMock()
    uc.execute_initial.side_effect = UnsupportedProtocolError("psd2")
    app = _build_app(use_case=uc)
    async with _client(app) as client:
        resp = await client.post("/v1/transactions/fetch", json=_initial_body())
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "UNSUPPORTED_PROTOCOL"


@pytest.mark.asyncio
async def test_bank_not_supported_returns_422() -> None:
    uc = AsyncMock()
    uc.execute_initial.side_effect = BankNotSupportedError("99999999", "fints")
    app = _build_app(use_case=uc)
    async with _client(app) as client:
        resp = await client.post("/v1/transactions/fetch", json=_initial_body())
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "BANK_NOT_SUPPORTED"


@pytest.mark.asyncio
async def test_tan_rejected_returns_422() -> None:
    uc = AsyncMock()
    uc.execute_resume.side_effect = TANRejectedError("sess-abc", "wrong TAN")
    app = _build_app(use_case=uc)
    async with _client(app) as client:
        resp = await client.post("/v1/transactions/fetch", json=_resume_body())
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "TAN_REJECTED"


@pytest.mark.asyncio
async def test_bank_connection_error_returns_502() -> None:
    uc = AsyncMock()
    uc.execute_initial.side_effect = BankConnectionError("12345678", "timeout")
    app = _build_app(use_case=uc)
    async with _client(app) as client:
        resp = await client.post("/v1/transactions/fetch", json=_initial_body())
    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "BANK_CONNECTION_ERROR"


@pytest.mark.asyncio
async def test_missing_fields_returns_422() -> None:
    app = _build_app()
    async with _client(app) as client:
        resp = await client.post("/v1/transactions/fetch", json={})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_audit_event_published_on_success() -> None:
    uc = AsyncMock()
    uc.execute_initial.return_value = _make_success_result()
    ap = AsyncMock()
    app = _build_app(use_case=uc, audit_publisher=ap)
    async with _client(app) as client:
        await client.post("/v1/transactions/fetch", json=_initial_body())
    await asyncio.sleep(0.05)
    ap.publish.assert_awaited_once()
    event = ap.publish.call_args[0][0]
    assert event.account_id == "acct-test"
    assert event.request_type == "/v1/transactions/fetch"
    assert event.protocol == BankingProtocol.FINTS


@pytest.mark.asyncio
async def test_version_endpoint_returns_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_COMMIT_HASH", "abc123")
    monkeypatch.setenv("DOCKER_IMAGE_SHA256", "sha256:def456")
    app = _build_app()
    async with _client(app) as client:
        resp = await client.get("/v1/system/version")
    assert resp.status_code == 200
    data = resp.json()
    assert data["git_commit_hash"] == "abc123"
    assert data["docker_image_sha256"] == "sha256:def456"


@pytest.mark.asyncio
async def test_version_unknown_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GIT_COMMIT_HASH", raising=False)
    monkeypatch.delenv("DOCKER_IMAGE_SHA256", raising=False)
    app = _build_app()
    async with _client(app) as client:
        resp = await client.get("/v1/system/version")
    assert resp.status_code == 200
    data = resp.json()
    assert data["git_commit_hash"] == "unknown"
    assert data["docker_image_sha256"] == "unknown"
