"""SQL repository for the shared FinTS product registration."""

from __future__ import annotations

from gateway_contracts.schema import fints_product_registration_table
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine

from gateway.domain.banking_gateway import (
    FinTSProductRegistration,
    FinTSProductRegistrationRepository,
)


class FinTSProductRegistrationRepositorySqlAlchemy(FinTSProductRegistrationRepository):
    """Persist the singleton product registration in a SQL database."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def get_current(self) -> FinTSProductRegistration | None:
        statement = select(fints_product_registration_table).where(
            fints_product_registration_table.c.singleton_key.is_(True)
        )
        async with self._engine.connect() as connection:
            row = (await connection.execute(statement)).mappings().first()
        return _row_to_registration(row) if row is not None else None


def _row_to_registration(row: object) -> FinTSProductRegistration:
    mapping = dict(row)
    return FinTSProductRegistration(
        product_key=mapping["product_key"],
        product_version=mapping["product_version"],
        updated_at=mapping["updated_at"],
    )
