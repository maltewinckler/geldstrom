"""Startup and shutdown lifecycle for the gateway backend."""

from __future__ import annotations

from gateway.presentation.http.dependencies import get_factory


async def startup() -> None:
    await get_factory().startup()


async def shutdown() -> None:
    await get_factory().shutdown()
