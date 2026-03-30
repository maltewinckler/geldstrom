"""E2E: health liveness endpoint — sanity check that the app started correctly."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient


@pytest.mark.e2e
def test_liveness_returns_200(app_client: TestClient) -> None:
    """GET /health/live must return 200 once the app has started."""
    resp = app_client.get("/health/live")
    assert resp.status_code == 200
