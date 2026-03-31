"""Tests for the health router."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from starlette.testclient import TestClient

from gateway.application.common import ReadinessStatus
from gateway.presentation.http.dependencies import get_factory
from gateway.presentation.http.routers.health import router


def _make_app(*, readiness_status: ReadinessStatus | None = None) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    if readiness_status is not None:
        mock_readiness_service = MagicMock()
        mock_readiness_service.check = AsyncMock(return_value=readiness_status)
        mock_factory = MagicMock()
        mock_factory.readiness_service = mock_readiness_service
        app.dependency_overrides[get_factory] = lambda: mock_factory
    return app


def test_liveness_returns_200_ok() -> None:
    client = TestClient(_make_app())
    resp = client.get("/health/live")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_readiness_returns_200_when_all_checks_pass() -> None:
    client = TestClient(
        _make_app(
            readiness_status=ReadinessStatus(db=True, product_key=True, catalog=True)
        )
    )
    resp = client.get("/health/ready")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["checks"]["db"] == "ok"
    assert body["checks"]["product_key"] == "loaded"
    assert body["checks"]["catalog"] == "ok"


def test_readiness_returns_503_when_catalog_empty() -> None:
    client = TestClient(
        _make_app(
            readiness_status=ReadinessStatus(db=True, product_key=True, catalog=False)
        )
    )
    resp = client.get("/health/ready")

    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["catalog"] == "empty"


def test_readiness_returns_503_when_db_unreachable() -> None:
    client = TestClient(
        _make_app(
            readiness_status=ReadinessStatus(db=False, product_key=False, catalog=False)
        )
    )
    resp = client.get("/health/ready")

    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["db"] == "error"


def test_readiness_returns_503_when_product_key_missing() -> None:
    client = TestClient(
        _make_app(
            readiness_status=ReadinessStatus(db=True, product_key=False, catalog=True)
        )
    )
    resp = client.get("/health/ready")

    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["product_key"] == "missing"
