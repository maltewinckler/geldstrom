"""PostgreSQL/SQLAlchemy repository for users (API consumers)."""

from __future__ import annotations

from typing import Any

from gateway_contracts.schema import api_consumers_table
from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncEngine

from gateway_admin.domain.entities.users import User, UserStatus
from gateway_admin.domain.value_objects.user import ApiKeyHash, Email, UserId


class UserRepositorySQLAlchemy:
    """Persist user (API consumer) records in PostgreSQL."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def get_by_id(self, user_id: UserId) -> User | None:
        stmt = select(api_consumers_table).where(
            api_consumers_table.c.consumer_id == user_id.value
        )
        async with self._engine.connect() as conn:
            row = (await conn.execute(stmt)).mappings().first()
        return _row_to_user(row) if row is not None else None

    async def get_by_email(self, email: Email) -> User | None:
        stmt = select(api_consumers_table).where(
            api_consumers_table.c.email == email.value
        )
        async with self._engine.connect() as conn:
            row = (await conn.execute(stmt)).mappings().first()
        return _row_to_user(row) if row is not None else None

    async def save(self, user: User) -> None:
        payload = {
            "consumer_id": user.user_id.value,
            "email": user.email.value,
            "api_key_hash": user.api_key_hash.value if user.api_key_hash else None,
            "status": user.status.value,
            "created_at": user.created_at,
            "rotated_at": user.rotated_at,
        }
        async with self._engine.begin() as conn:
            existing = (
                await conn.execute(
                    select(api_consumers_table).where(
                        api_consumers_table.c.consumer_id == user.user_id.value
                    )
                )
            ).first()
            if existing is None:
                await conn.execute(insert(api_consumers_table).values(**payload))
            else:
                await conn.execute(
                    update(api_consumers_table)
                    .where(api_consumers_table.c.consumer_id == user.user_id.value)
                    .values(**{k: v for k, v in payload.items() if k != "consumer_id"})
                )

    async def list_all(self) -> list[User]:
        stmt = select(api_consumers_table).order_by(api_consumers_table.c.email.asc())
        async with self._engine.connect() as conn:
            rows = (await conn.execute(stmt)).mappings().all()
        return [_row_to_user(row) for row in rows]


def _row_to_user(row: Any) -> User:
    mapping = dict(row)
    return User(
        user_id=UserId(mapping["consumer_id"]),
        email=Email(mapping["email"]),
        api_key_hash=ApiKeyHash(mapping["api_key_hash"])
        if mapping["api_key_hash"]
        else None,
        status=UserStatus(mapping["status"]),
        created_at=mapping["created_at"],
        rotated_at=mapping.get("rotated_at"),
    )
