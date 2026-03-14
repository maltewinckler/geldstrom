"""Tests for the health router."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from starlette.testclient import TestClient

from gateway.application.health.queries.evaluate_health import EvaluateHealthQuery
from gateway.presentation.http.dependencies import get_factory_dep
from gateway.presentation.http.routers.health import router


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_factory_dep] = lambda: MagicMock()
    return app


def test_liveness_returns_200_ok() -> None:
    use_case = AsyncMock()
    use_case.live = AsyncMock(return_value={"status": "ok"})
    with patch.object(EvaluateHealthQuery, "from_factory", return_value=use_case):
        client = TestClient(_make_app())
        resp = client.get("/health/live")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_readiness_returns_200_when_all_checks_pass() -> None:
    use_case = AsyncMock()
    use_case.ready = AsyncMock(return_value={"status": "ready", "checks": {"db": "ok"}})
    with patch.object(EvaluateHealthQuery, "from_factory", return_value=use_case):
        client = TestClient(_make_app())
        resp = client.get("/health/ready")

    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


def test_readiness_returns_503_when_a_check_fails() -> None:
    use_case = AsyncMock()
    use_case.ready = AsyncMock(
        return_value={"status": "not_ready", "checks": {"db": "failed"}}
    )
    with patch.object(EvaluateHealthQuery, "from_factory", return_value=use_case):
        client = TestClient(_make_app())
        resp = client.get("/health/ready")

    assert resp.status_code == 503
    assert resp.json()["status"] == "not_ready"
