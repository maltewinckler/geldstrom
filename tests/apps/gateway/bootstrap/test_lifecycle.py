"""Tests for the gateway startup/shutdown lifecycle."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from gateway.infrastructure.gateway_factory import GatewayApplicationFactory
from gateway.presentation.http.lifecycle import shutdown, startup

# ---------------------------------------------------------------------------
# startup / shutdown — delegation to factory
# ---------------------------------------------------------------------------


def test_startup_delegates_to_factory() -> None:
    factory = AsyncMock()

    with patch("gateway.presentation.http.lifecycle.get_factory", return_value=factory):
        asyncio.run(startup())

    factory.startup.assert_awaited_once()


def test_shutdown_delegates_to_factory() -> None:
    factory = AsyncMock()

    with patch("gateway.presentation.http.lifecycle.get_factory", return_value=factory):
        asyncio.run(shutdown())

    factory.shutdown.assert_awaited_once()


# ---------------------------------------------------------------------------
# GatewayApplicationFactory.startup — _warm_product_key removed (Req 6.1)
# ---------------------------------------------------------------------------


def test_warm_product_key_not_called_during_startup() -> None:
    """startup() must not invoke _warm_product_key — it has been removed.

    Validates: Requirements 6.1
    """
    settings = MagicMock()
    settings.redis_url = "redis://localhost:6379"
    settings.database_url.get_secret_value.return_value = (
        "postgresql+asyncpg://user:pass@localhost/db"
    )
    settings.notify_reconnect_backoff_seconds = 1.0

    factory = GatewayApplicationFactory(settings)

    # _warm_product_key must not exist on the factory at all
    assert not hasattr(factory, "_warm_product_key"), (
        "_warm_product_key should have been removed from GatewayApplicationFactory"
    )

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock()

    with (
        patch(
            "gateway.infrastructure.gateway_factory.Redis.from_url",
            return_value=mock_redis,
        ),
        patch.object(factory, "_start_notify_listener", new_callable=AsyncMock),
        patch.object(factory, "_warm_institute_cache", new_callable=AsyncMock),
    ):
        asyncio.run(factory.startup())

    # Confirm startup completed without any product-key warming
    assert not hasattr(factory, "_warm_product_key")
