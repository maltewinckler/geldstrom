"""Workspace-level unit tests for the monorepo foundation."""

import importlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# --- Package importability tests ---


@pytest.mark.parametrize("package_name", ["geldstrom", "gateway", "admin"])
def test_workspace_package_imports(package_name: str) -> None:
    """Each workspace package top-level module imports without error."""
    mod = importlib.import_module(package_name)
    assert mod is not None


# --- Health endpoint tests ---


def test_gateway_health() -> None:
    """GET /health on gateway app returns {"status": "ok"}."""
    from gateway.api.main import app

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_admin_health() -> None:
    """GET /health on admin app returns {"status": "ok"}."""
    from admin.api.main import app

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# --- Admin UI no Python deps test ---


def test_admin_ui_no_python_deps() -> None:
    """apps/admin-ui/package.json contains no Python package names."""
    package_json = Path("apps/admin-ui/package.json")
    assert package_json.exists(), "apps/admin-ui/package.json not found"
    data = json.loads(package_json.read_text())
    python_packages = {
        "geldstrom",
        "gateway",
        "admin",
        "fastapi",
        "sqlalchemy",
        "asyncpg",
        "alembic",
    }
    all_deps = set(data.get("dependencies", {}).keys()) | set(
        data.get("devDependencies", {}).keys()
    )
    assert not all_deps & python_packages, (
        f"Python packages found in admin-ui deps: {all_deps & python_packages}"
    )


# --- Makefile targets test ---


def test_makefile_targets() -> None:
    """Makefile contains install, proto, lint, test targets."""
    makefile = Path("Makefile")
    assert makefile.exists(), "Makefile not found"
    content = makefile.read_text()
    for target in ["install", "proto", "lint", "test"]:
        assert f"{target}:" in content, f"Makefile missing target: {target}"
