"""Shared CLI helpers: factory construction."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from gateway_admin_cli.config import get_settings
from gateway_admin_cli.infrastructure.admin_factory import ConcreteAdminFactory


@asynccontextmanager
async def build_factory() -> AsyncIterator[ConcreteAdminFactory]:
    s = get_settings()
    factory = ConcreteAdminFactory(
        database_url=s.database_url,
        argon2_time_cost=s.admin_argon2_time_cost,
        argon2_memory_cost=s.admin_argon2_memory_cost,
        argon2_parallelism=s.admin_argon2_parallelism,
    )
    try:
        yield factory
    finally:
        await factory.dispose()
