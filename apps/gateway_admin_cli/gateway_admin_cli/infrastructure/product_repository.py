"""PostgreSQL repository for the shared product registration."""

from __future__ import annotations

from typing import Any

from gateway_contracts.schema import fints_product_registration_table
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine

from gateway_admin_cli.domain.product import ProductRegistration

_SINGLETON_KEY = True


class PostgresProductRegistrationRepository:
    """Persist the shared FinTS product registration in PostgreSQL."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def get_current(self) -> ProductRegistration | None:
        stmt = select(fints_product_registration_table).where(
            fints_product_registration_table.c.singleton_key == _SINGLETON_KEY
        )
        async with self._engine.connect() as conn:
            row = (await conn.execute(stmt)).mappings().first()
        return _row_to_registration(row) if row is not None else None

    async def save_current(self, registration: ProductRegistration) -> None:
        payload = {
            "singleton_key": _SINGLETON_KEY,
            "product_key": registration.product_key,
            "product_version": registration.product_version,
            "updated_at": registration.updated_at,
        }
        stmt = (
            insert(fints_product_registration_table)
            .values(**payload)
            .on_conflict_do_update(
                index_elements=["singleton_key"],
                set_={k: v for k, v in payload.items() if k != "singleton_key"},
            )
        )
        async with self._engine.begin() as conn:
            await conn.execute(stmt)


def _row_to_registration(row: Any) -> ProductRegistration:
    mapping = dict(row)
    return ProductRegistration(
        product_key=mapping["product_key"],
        product_version=mapping["product_version"],
        updated_at=mapping["updated_at"],
    )
