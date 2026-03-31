"""Shared pytest fixtures for gateway tests.

PostgreSQL-backed gateway tests always run against a disposable testcontainer.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable, Generator
from pathlib import Path
from typing import TypeVar

import pytest
from gateway_contracts.schema import (
    create_test_schema,
    drop_test_schema,
)
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine

from gateway.infrastructure.persistence.sql.connection import build_engine


def _ensure_docker_host() -> None:
    """Point the Docker client at the Podman socket when Docker is absent."""
    if "DOCKER_HOST" in os.environ:
        return
    podman_sock = Path(f"/run/user/{os.getuid()}/podman/podman.sock")
    if podman_sock.exists():
        os.environ["DOCKER_HOST"] = f"unix://{podman_sock}"


_ensure_docker_host()

T = TypeVar("T")


@pytest.fixture
def async_runner() -> Generator[Callable[[Awaitable[T]], T]]:
    loop = asyncio.new_event_loop()
    try:
        yield loop.run_until_complete
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()


@pytest.fixture
def postgres_engine(
    postgres_database_url: str,
    async_runner: Callable[[Awaitable[object]], object],
) -> Generator[AsyncEngine]:
    engine = build_engine(postgres_database_url, use_null_pool=True)
    async_runner(drop_test_schema(engine))
    async_runner(create_test_schema(engine))
    try:
        yield engine
    finally:
        async_runner(drop_test_schema(engine))
        async_runner(engine.dispose())


@pytest.fixture(scope="session")
def postgres_database_url() -> Generator[str]:
    testcontainers = pytest.importorskip("testcontainers.postgres")
    try:
        container = testcontainers.PostgresContainer("postgres:16-alpine")
        container.start()
    except Exception as exc:
        pytest.skip(f"Unable to start PostgreSQL testcontainer: {exc}")

    try:
        yield _to_asyncpg_url(container.get_connection_url())
    finally:
        container.stop()


def _to_asyncpg_url(database_url: str) -> str:
    url = make_url(database_url)
    return url.set(drivername="postgresql+asyncpg").render_as_string(
        hide_password=False
    )
