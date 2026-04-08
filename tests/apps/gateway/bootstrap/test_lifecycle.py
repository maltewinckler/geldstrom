"""Tests for the gateway startup/shutdown lifecycle."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

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
