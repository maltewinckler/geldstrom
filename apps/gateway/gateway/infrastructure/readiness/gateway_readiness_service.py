"""PostgreSQL-backed gateway readiness service."""

from __future__ import annotations

from gateway_contracts.schema import (
    fints_institutes_table,
    fints_product_registration_table,
)
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine

from gateway.application.common.readiness import ReadinessStatus
from gateway.application.ports.gateway_readiness_service import GatewayReadinessPort


class SQLGatewayReadinessService(GatewayReadinessPort):
    """Check gateway readiness by querying PostgreSQL directly.

    Three checks against the database:
    - ``db``: a lightweight ``SELECT 1`` connectivity ping.
    - ``product_key``: whether a product registration row exists.
    - ``catalog``: whether at least one FinTS institute row exists.
    """

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def check(self) -> ReadinessStatus:
        db_ok = await self._ping()
        if not db_ok:
            return ReadinessStatus(db=False, product_key=False, catalog=False)
        product_key_ok = await self._product_key_exists()
        catalog_ok = await self._catalog_has_rows()
        return ReadinessStatus(db=True, product_key=product_key_ok, catalog=catalog_ok)

    async def _ping(self) -> bool:
        try:
            async with self._engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    async def _product_key_exists(self) -> bool:
        try:
            stmt = (
                select(fints_product_registration_table.c.singleton_key)
                .where(fints_product_registration_table.c.singleton_key.is_(True))
                .limit(1)
            )
            async with self._engine.connect() as conn:
                result = await conn.scalar(stmt)
            return result is not None
        except Exception:
            return False

    async def _catalog_has_rows(self) -> bool:
        try:
            stmt = select(fints_institutes_table.c.blz).limit(1)
            async with self._engine.connect() as conn:
                result = await conn.scalar(stmt)
            return result is not None
        except Exception:
            return False
