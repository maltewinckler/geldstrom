"""End-to-end test fixtures.

Fixture pyramid (all session-scoped — the full setup runs once per pytest session):

    postgres_container        single disposable PostgreSQL testcontainer
        └── seeded_db_url     schema + catalog + product registration seeded via
                              admin-CLI application layer (no subprocess)
                └── e2e_api_key   one test user; raw key stashed for request auth
    app_client                starlette.testclient.TestClient wrapping the real
                              FastAPI app pointed at the seeded container

Run with:
    uv run pytest tests/end_to_end/ --run-e2e
    uv run pytest tests/end_to_end/ --run-e2e --run-e2e-tan   # includes 2FA tests
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy.engine import make_url
from starlette.testclient import TestClient

# ---------------------------------------------------------------------------
# CLI option registration
# ---------------------------------------------------------------------------


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-e2e",
        action="store_true",
        default=False,
        help="Run end-to-end tests (requires .env with bank credentials).",
    )
    parser.addoption(
        "--run-e2e-tan",
        action="store_true",
        default=False,
        help="Also run e2e tests that deliberately trigger a 2FA challenge (200-day window).",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if not config.getoption("--run-e2e"):
        skip = pytest.mark.skip(reason="use --run-e2e to run end-to-end tests")
        for item in items:
            if "e2e" in item.keywords or "e2e_tan" in item.keywords:
                item.add_marker(skip)
        return

    if not config.getoption("--run-e2e-tan"):
        skip_tan = pytest.mark.skip(
            reason="use --run-e2e-tan to run 2FA-triggering tests"
        )
        for item in items:
            if "e2e_tan" in item.keywords:
                item.add_marker(skip_tan)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_asyncpg_url(psycopg2_url: str) -> str:
    url = make_url(psycopg2_url)
    return url.set(drivername="postgresql+asyncpg").render_as_string(
        hide_password=False
    )


def _ensure_docker_host() -> None:
    if "DOCKER_HOST" in os.environ:
        return
    podman_sock = Path(f"/run/user/{os.getuid()}/podman/podman.sock")
    if podman_sock.exists():
        os.environ["DOCKER_HOST"] = f"unix://{podman_sock}"


_ensure_docker_host()


# ---------------------------------------------------------------------------
# Banking credentials from .env
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def e2e_credentials() -> dict[str, str]:
    """Load FinTS banking credentials from .env in the repository root.

    Skips the entire session if any required variable is missing.
    """
    load_dotenv(Path(".env"), override=False)

    required = [
        "FINTS_BLZ",
        "FINTS_USER",
        "FINTS_PIN",
        "FINTS_SERVER",
        "FINTS_PRODUCT_ID",
        "FINTS_TAN_METHOD",
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        pytest.skip(f"Missing .env variables: {', '.join(missing)}")

    return {
        "blz": os.environ["FINTS_BLZ"],
        "user_id": os.environ["FINTS_USER"],
        "password": os.environ["FINTS_PIN"],
        "server": os.environ["FINTS_SERVER"],
        "product_id": os.environ["FINTS_PRODUCT_ID"],
        "product_version": os.getenv("FINTS_PRODUCT_VERSION", "1.0.0"),
        "tan_method": os.environ["FINTS_TAN_METHOD"],
        "tan_medium": os.getenv("FINTS_TAN_MEDIUM", ""),
    }


# ---------------------------------------------------------------------------
# PostgreSQL testcontainer
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def e2e_postgres_url() -> str:
    """Start a disposable PostgreSQL container and return its asyncpg URL."""
    testcontainers = pytest.importorskip("testcontainers.postgres")
    try:
        container = testcontainers.PostgresContainer("postgres:16-alpine")
        container.start()
    except Exception as exc:
        pytest.skip(f"Cannot start PostgreSQL testcontainer: {exc}")

    url = _to_asyncpg_url(container.get_connection_url())

    yield url

    container.stop()


# ---------------------------------------------------------------------------
# Database seeding via admin-CLI application layer
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def seeded_db_url(e2e_postgres_url: str, e2e_credentials: dict[str, str]) -> str:
    """Create the schema, sync the institute catalog, and register the product.

    Uses the admin-CLI application commands directly (no subprocess).
    Returns the asyncpg database URL.
    """
    from gateway_contracts.schema import create_test_schema

    from gateway_admin.application.commands.sync_institute_catalog import (
        SyncInstituteCatalogCommand,
    )
    from gateway_admin.application.commands.update_product_registration import (
        UpdateProductRegistrationCommand,
    )
    from gateway_admin.infrastructure.admin_factory import ConcreteAdminFactory

    async def _seed() -> None:
        from gateway.infrastructure.persistence.sqlalchemy.connection import (
            build_engine,
        )

        # Create schema
        engine = build_engine(e2e_postgres_url, use_null_pool=True)
        await create_test_schema(engine)
        await engine.dispose()

        # Seed via admin factory (lower argon2 cost for speed)
        factory = ConcreteAdminFactory(
            database_url=e2e_postgres_url,
            argon2_time_cost=1,
            argon2_memory_cost=8192,
            argon2_parallelism=1,
        )
        try:
            await SyncInstituteCatalogCommand.from_factory(factory)(
                Path("data/fints_institute.csv")
            )
            await UpdateProductRegistrationCommand.from_factory(
                factory,
                product_version=e2e_credentials["product_version"],
            )(e2e_credentials["product_id"])
        finally:
            await factory.dispose()

    asyncio.run(_seed())
    return e2e_postgres_url


# ---------------------------------------------------------------------------
# Test user + API key
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def e2e_api_key(seeded_db_url: str) -> str:
    """Create a test user in the seeded DB and return the raw API key."""
    from gateway_admin.application.commands.create_user import CreateUserCommand
    from gateway_admin.infrastructure.admin_factory import ConcreteAdminFactory

    async def _create_user() -> str:
        factory = ConcreteAdminFactory(
            database_url=seeded_db_url,
            argon2_time_cost=1,
            argon2_memory_cost=8192,
            argon2_parallelism=1,
        )
        try:
            result = await CreateUserCommand.from_factory(factory)("e2e@example.com")
        finally:
            await factory.dispose()
        return result.raw_api_key

    return asyncio.run(_create_user())


# ---------------------------------------------------------------------------
# Gateway app client
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def app_client(seeded_db_url: str, e2e_api_key: str) -> TestClient:  # noqa: ARG001
    """Starlette TestClient wrapping the real gateway app.

    Depends on ``e2e_api_key`` (not used directly) to guarantee the test user
    is written to the database *before* the gateway starts and warms its
    consumer cache.  Without this ordering the cache misses the user and every
    authenticated request returns 401.

    The individual GATEWAY_DB_* env vars are set (not GATEWAY_DATABASE_URL,
    which the Settings class doesn't support) so the app connects to the
    testcontainer rather than the 'postgres' Docker hostname.  Argon2 cost is
    lowered for speed.
    """
    from sqlalchemy.engine import make_url

    from gateway.presentation.http.api import create_app
    from gateway.presentation.http.dependencies import get_factory, get_settings

    # Parse the asyncpg testcontainer URL into individual GATEWAY_DB_* vars
    # that the Settings class actually reads.
    parsed = make_url(seeded_db_url)
    os.environ["GATEWAY_DB_HOST"] = parsed.host or "localhost"
    os.environ["GATEWAY_DB_PORT"] = str(parsed.port or 5432)
    os.environ["GATEWAY_DB_USER"] = parsed.username or "test"
    os.environ["GATEWAY_DB_PASSWORD"] = parsed.password or "test"
    os.environ["GATEWAY_DB_NAME"] = (parsed.database or "test").lstrip("/")
    os.environ["GATEWAY_ARGON2_TIME_COST"] = "1"
    os.environ["GATEWAY_ARGON2_MEMORY_COST"] = "8192"
    os.environ["GATEWAY_ARGON2_PARALLELISM"] = "1"

    # Clear caches so the overridden env vars are picked up
    get_settings.cache_clear()
    get_factory.cache_clear()

    app = create_app()

    # TestClient as context manager runs the full lifespan (startup → tests → shutdown)
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client

    get_settings.cache_clear()
    get_factory.cache_clear()
