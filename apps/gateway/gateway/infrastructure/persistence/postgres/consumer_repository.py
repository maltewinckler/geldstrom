"""PostgreSQL repository for API consumer aggregates."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.ext.asyncio import AsyncEngine

from gateway.domain.consumer_access import (
    ApiConsumer,
    ApiConsumerRepository,
    ApiKeyHash,
    ConsumerId,
    ConsumerStatus,
    EmailAddress,
)

from .schema import api_consumers_table


class PostgresApiConsumerRepository(ApiConsumerRepository):
    """Persist API consumer aggregates in PostgreSQL."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def get_by_id(self, consumer_id: ConsumerId) -> ApiConsumer | None:
        statement = select(api_consumers_table).where(
            api_consumers_table.c.consumer_id == consumer_id.value
        )
        async with self._engine.connect() as connection:
            row = (await connection.execute(statement)).mappings().first()
        return _row_to_consumer(row) if row is not None else None

    async def get_by_email(self, email: EmailAddress) -> ApiConsumer | None:
        statement = select(api_consumers_table).where(
            api_consumers_table.c.email == email.value
        )
        async with self._engine.connect() as connection:
            row = (await connection.execute(statement)).mappings().first()
        return _row_to_consumer(row) if row is not None else None

    async def list_all(self) -> list[ApiConsumer]:
        statement = select(api_consumers_table).order_by(api_consumers_table.c.email.asc())
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

    async def save(self, consumer: ApiConsumer) -> None:
        statement = postgres_insert(api_consumers_table).values(
            consumer_id=consumer.consumer_id.value,
            email=consumer.email.value,
            api_key_hash=consumer.api_key_hash.value if consumer.api_key_hash else None,
            status=consumer.status.value,
            created_at=consumer.created_at,
            rotated_at=consumer.rotated_at,
        )
        statement = statement.on_conflict_do_update(
            index_elements=[api_consumers_table.c.consumer_id],
            set_={
                "email": consumer.email.value,
                "api_key_hash": consumer.api_key_hash.value
                if consumer.api_key_hash
                else None,
                "status": consumer.status.value,
                "created_at": consumer.created_at,
                "rotated_at": consumer.rotated_at,
            },
        )
        async with self._engine.begin() as connection:
            await connection.execute(statement)


def _row_to_consumer(row: object) -> ApiConsumer:
    mapping = dict(row)
    return ApiConsumer(
        consumer_id=ConsumerId(mapping["consumer_id"]),
        email=EmailAddress(mapping["email"]),
        api_key_hash=(
            ApiKeyHash(mapping["api_key_hash"]) if mapping["api_key_hash"] else None
        ),
        status=ConsumerStatus(mapping["status"]),
        created_at=mapping["created_at"],
        rotated_at=mapping["rotated_at"],
    )
