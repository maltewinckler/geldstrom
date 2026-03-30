"""Tests for the health router."""

from __future__ import annotations

from fastapi import FastAPI
from starlette.testclient import TestClient

from gateway.presentation.http.routers.health import router


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


def test_liveness_returns_200_ok() -> None:
    client = TestClient(_make_app())
    resp = client.get("/health/live")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
