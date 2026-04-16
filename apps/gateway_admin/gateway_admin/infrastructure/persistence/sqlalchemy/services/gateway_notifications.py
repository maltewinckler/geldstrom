"""PostgreSQL NOTIFY implementation of GatewayNotificationService.

Sends pg_notify messages on the channels defined in gateway-contracts so the
running gateway process can invalidate its in-memory caches.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from gateway_contracts.channels import (
    CATALOG_REPLACED_CHANNEL,
    CONSUMER_UPDATED_CHANNEL,
    PRODUCT_REGISTRATION_UPDATED_CHANNEL,
)
from gateway_contracts.payloads import ConsumerUpdatedPayload
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from gateway_admin.domain.services.gateway_notifications import (
    GatewayNotificationService,
)

if TYPE_CHECKING:
    from gateway_admin.application.factories.admin_factory import AdminRepositoryFactory

_NOTIFY_SQL = text("SELECT pg_notify(:channel, :payload)")


class GatewayNotificationServiceSQLAlchemy(GatewayNotificationService):
    """Sends gateway cache-invalidation notifications via PostgreSQL NOTIFY."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    @classmethod
    def from_factory(cls, repo_factory: AdminRepositoryFactory) -> Self:
        from gateway_admin.infrastructure.persistence.sqlalchemy.factories.admin_factory import (
            AdminRepositoryFactorySQLAlchemy,
        )

        assert isinstance(repo_factory, AdminRepositoryFactorySQLAlchemy)
        return cls(repo_factory._engine)

    async def notify_user_updated(self, user_id: str) -> None:
        payload = ConsumerUpdatedPayload(consumer_id=user_id)
        async with self._engine.begin() as conn:
            await conn.execute(
                _NOTIFY_SQL,
                {"channel": CONSUMER_UPDATED_CHANNEL, "payload": payload.serialize()},
            )

    async def notify_institute_catalog_replaced(self) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                _NOTIFY_SQL,
                {"channel": CATALOG_REPLACED_CHANNEL, "payload": "{}"},
            )

    async def notify_product_registration_updated(self) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                _NOTIFY_SQL,
                {"channel": PRODUCT_REGISTRATION_UPDATED_CHANNEL, "payload": "{}"},
            )
