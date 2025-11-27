"""Project-wide pytest helpers."""
from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-integration",
        action="store_true",
        help=(
            "Execute integration tests that hit real bank backends "
            "(requires .env credentials)."
        ),
    )
    parser.addoption(
        "--fints-env-file",
        default=".env",
        help="Path to the .env file consumed by integration tests (default: .env).",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: requires live FinTS credentials and TAN approval.",
    )


def pytest_collection_modifyitems(config: pytest.Config, items):
    if config.getoption("--run-integration"):
        return
    skip_marker = pytest.mark.skip(
        reason="integration tests disabled (use --run-integration to enable)",
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_marker)
