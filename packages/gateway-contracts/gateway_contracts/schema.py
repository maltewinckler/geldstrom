"""SQLAlchemy schema metadata shared between gateway and admin CLI."""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    MetaData,
    String,
    Table,
    Uuid,
)
from sqlalchemy.ext.asyncio import AsyncEngine

metadata = MetaData()

api_consumers_table = Table(
    "api_consumers",
    metadata,
    Column("consumer_id", Uuid(as_uuid=True), primary_key=True),
    Column("email", String(320), nullable=False, unique=True),
    Column("api_key_hash", String(1024), nullable=True),
    Column("status", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("rotated_at", DateTime(timezone=True), nullable=True),
)

fints_institutes_table = Table(
    "fints_institutes",
    metadata,
    Column("blz", String(8), primary_key=True),
    Column("bic", String(11), nullable=True),
    Column("name", String(255), nullable=False),
    Column("city", String(255), nullable=True),
    Column("organization", String(255), nullable=True),
    Column("pin_tan_url", String(1024), nullable=True),
    Column("fints_version", String(64), nullable=True),
    Column("last_source_update", Date(), nullable=True),
    Column("source_row_checksum", String(64), nullable=False),
    Column("source_payload", JSON, nullable=False),
)

fints_product_registration_table = Table(
    "fints_product_registration",
    metadata,
    Column("singleton_key", Boolean(), primary_key=True, default=True),
    Column("product_key", String(256), nullable=False),
    Column("product_version", String(64), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)


audit_events_table = Table(
    "audit_events",
    metadata,
    Column("event_id", Uuid(as_uuid=True), primary_key=True),
    Column("event_type", String(64), nullable=False),
    Column("consumer_id", Uuid(as_uuid=True), nullable=True),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
)


async def create_test_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(metadata.create_all)


async def drop_test_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(metadata.drop_all)
