"""PostgreSQL repository for the shared FinTS product registration."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.ext.asyncio import AsyncEngine

from gateway.domain.product_registration import (
    EncryptedProductKey,
    FinTSProductRegistration,
    FinTSProductRegistrationRepository,
    KeyVersion,
    ProductVersion,
)
from gateway.domain.shared import EntityId

from .schema import fints_product_registration_table


class PostgresFinTSProductRegistrationRepository(FinTSProductRegistrationRepository):
    """Persist the singleton product registration in PostgreSQL."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def get_current(self) -> FinTSProductRegistration | None:
        statement = select(fints_product_registration_table).where(
            fints_product_registration_table.c.singleton_key.is_(True)
        )
        async with self._engine.connect() as connection:
            row = (await connection.execute(statement)).mappings().first()
        return _row_to_registration(row) if row is not None else None

    async def save_current(self, registration: FinTSProductRegistration) -> None:
        statement = postgres_insert(fints_product_registration_table).values(
            singleton_key=True,
            registration_id=registration.registration_id.value,
            encrypted_product_key=registration.encrypted_product_key.value,
            product_version=registration.product_version.value,
            key_version=registration.key_version.value,
            updated_at=registration.updated_at,
        )
        statement = statement.on_conflict_do_update(
            index_elements=[fints_product_registration_table.c.singleton_key],
            set_={
                "registration_id": registration.registration_id.value,
                "encrypted_product_key": registration.encrypted_product_key.value,
                "product_version": registration.product_version.value,
                "key_version": registration.key_version.value,
                "updated_at": registration.updated_at,
            },
        )
        async with self._engine.begin() as connection:
            await connection.execute(statement)


def _row_to_registration(row: object) -> FinTSProductRegistration:
    mapping = dict(row)
    return FinTSProductRegistration(
        registration_id=EntityId(mapping["registration_id"]),
        encrypted_product_key=EncryptedProductKey(
            bytes(mapping["encrypted_product_key"])
        ),
        product_version=ProductVersion(mapping["product_version"]),
        key_version=KeyVersion(mapping["key_version"]),
        updated_at=mapping["updated_at"],
    )
