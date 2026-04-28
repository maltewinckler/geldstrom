"""SQL repository for API consumer aggregates."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import sqlalchemy as sa
from gateway_contracts.schema import api_consumers_table
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine

from gateway.domain.consumer_access import (
    ApiConsumer,
    ApiConsumerRepository,
    ApiKeyHash,
    ConsumerStatus,
)

if TYPE_CHECKING:
    from sqlalchemy.engine import RowMapping


class ApiConsumerRepositorySqlAlchemy(ApiConsumerRepository):
    """Persist API consumer aggregates in a SQL database."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def get_by_id(self, consumer_id: UUID) -> ApiConsumer | None:
        statement = select(api_consumers_table).where(
            api_consumers_table.c.consumer_id == consumer_id
        )
        async with self._engine.connect() as connection:
            row = (await connection.execute(statement)).mappings().first()
        return _row_to_consumer(row)

    async def get_by_email(self, email: str) -> ApiConsumer | None:
        statement = select(api_consumers_table).where(
            api_consumers_table.c.email == email
        )
        async with self._engine.connect() as connection:
            row = (await connection.execute(statement)).mappings().first()
        return _row_to_consumer(row)

    async def list_all(self) -> list[ApiConsumer]:
        statement = select(api_consumers_table).order_by(
            api_consumers_table.c.email.asc()
        )
        async with self._engine.connect() as connection:
            rows = (await connection.execute(statement)).mappings().all()
        return [_row_to_consumer(row) for row in rows]

    async def list_all_active(self) -> list[ApiConsumer]:
        statement = select(api_consumers_table).where(
            api_consumers_table.c.status == ConsumerStatus.ACTIVE.value
        )
        async with self._engine.connect() as connection:
            rows = (await connection.execute(statement)).mappings().all()
        return [_row_to_consumer(row) for row in rows]

    async def get_by_key_prefix(self, prefix: str) -> ApiConsumer | None:
        cid_col = func.cast(api_consumers_table.c.consumer_id, type_=sa.Text)
        statement = (
            select(api_consumers_table)
            .where(func.left(cid_col, 8) == prefix)
            .where(
                api_consumers_table.c.status.in_(
                    [ConsumerStatus.ACTIVE.value, ConsumerStatus.DISABLED.value]
                )
            )
        )
        async with self._engine.connect() as connection:
            row = (await connection.execute(statement)).mappings().first()
        return _row_to_consumer(row)


def _row_to_consumer(row: RowMapping | None) -> ApiConsumer | None:
    if row is None:
        return None
    mapping = dict(row)
    return ApiConsumer(
        consumer_id=mapping["consumer_id"],
        email=mapping["email"],
        api_key_hash=(
            ApiKeyHash(mapping["api_key_hash"]) if mapping["api_key_hash"] else None
        ),
        status=ConsumerStatus(mapping["status"]),
        created_at=mapping["created_at"],
        rotated_at=mapping["rotated_at"],
    )
