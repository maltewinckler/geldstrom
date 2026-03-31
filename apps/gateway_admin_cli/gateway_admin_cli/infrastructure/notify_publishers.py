"""PostgreSQL NOTIFY publishers for gateway cache invalidation."""

from __future__ import annotations

from gateway_contracts.channels import (
    CATALOG_REPLACED_CHANNEL,
    CONSUMER_UPDATED_CHANNEL,
    PRODUCT_REGISTRATION_UPDATED_CHANNEL,
)
from gateway_contracts.payloads import ConsumerUpdatedPayload
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from gateway_admin_cli.domain.institutes import FinTSInstitute
from gateway_admin_cli.domain.product import ProductRegistration
from gateway_admin_cli.domain.users import User

_NOTIFY_SQL = text("SELECT pg_notify(:channel, :payload)")


class PostgresUserCacheWriter:
    """Invalidates the gateway's user cache via PostgreSQL NOTIFY."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def reload_one(self, user: User) -> None:
        payload = ConsumerUpdatedPayload(
            consumer_id=str(user.user_id),
        )
        async with self._engine.begin() as conn:
            await conn.execute(
                _NOTIFY_SQL,
                {"channel": CONSUMER_UPDATED_CHANNEL, "payload": payload.serialize()},
            )


class PostgresInstituteCacheLoader:
    """Signals the gateway to reload its institute cache via PostgreSQL NOTIFY."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def load(self, institutes: list[FinTSInstitute]) -> None:
        del institutes
        async with self._engine.begin() as conn:
            await conn.execute(
                _NOTIFY_SQL,
                {"channel": CATALOG_REPLACED_CHANNEL, "payload": "{}"},
            )


class PostgresProductRegistrationNotifier:
    """Signals the gateway to reload its product registration via PostgreSQL NOTIFY."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def set_current(self, registration: ProductRegistration | None) -> None:
        del registration
        async with self._engine.begin() as conn:
            await conn.execute(
                _NOTIFY_SQL,
                {"channel": PRODUCT_REGISTRATION_UPDATED_CHANNEL, "payload": "{}"},
            )
