"""Integration tests for PostgreSQL cache invalidation listeners."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, date, datetime
from uuid import UUID

from gateway_contracts.schema import api_consumers_table, fints_institutes_table
from sqlalchemy import text

from gateway.domain.banking_gateway import (
    BankLeitzahl,
    FinTSInstitute,
)
from gateway.domain.consumer_access import (
    ApiConsumer,
    ApiKeyHash,
    ConsumerStatus,
)
from gateway.infrastructure.cache.memory import (
    InMemoryApiConsumerCache,
    InMemoryFinTSInstituteCache,
    PostgresNotifyListener,
)
from gateway.infrastructure.persistence.postgres import (
    PostgresApiConsumerRepository,
    PostgresFinTSInstituteRepository,
)


async def _seed_consumer(engine, consumer: ApiConsumer) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            api_consumers_table.insert().values(
                consumer_id=consumer.consumer_id,
                email=consumer.email,
                api_key_hash=consumer.api_key_hash.value
                if consumer.api_key_hash
                else None,
                status=consumer.status.value,
                created_at=consumer.created_at,
                rotated_at=consumer.rotated_at,
            )
        )


async def _seed_institutes(engine, *institutes: FinTSInstitute) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            fints_institutes_table.insert(),
            [
                {
                    "blz": inst.blz.value,
                    "bic": inst.bic,
                    "name": inst.name,
                    "city": inst.city,
                    "organization": inst.organization,
                    "pin_tan_url": inst.pin_tan_url,
                    "fints_version": inst.fints_version,
                    "last_source_update": inst.last_source_update,
                    "source_row_checksum": inst.source_row_checksum,
                    "source_payload": inst.source_payload,
                }
                for inst in institutes
            ],
        )


def test_notify_listener_refreshes_one_consumer(postgres_engine, async_runner) -> None:
    async_runner(_exercise_consumer_notification(postgres_engine))


def test_notify_listener_reloads_catalog(postgres_engine, async_runner) -> None:
    async_runner(_exercise_catalog_notification(postgres_engine))


async def _exercise_consumer_notification(postgres_engine) -> None:
    repository = PostgresApiConsumerRepository(postgres_engine)
    cache = InMemoryApiConsumerCache()
    original = _consumer("consumer@example.com")
    updated = _consumer("updated@example.com", consumer_id=original.consumer_id)
    await _seed_consumer(postgres_engine, updated)
    await cache.load([original])
    listener = _build_listener(
        postgres_engine=postgres_engine,
        consumer_repository=repository,
        consumer_cache=cache,
    )

    await asyncio.wait_for(listener.start(), timeout=5.0)
    try:
        await _publish_notification(
            postgres_engine,
            "gw.consumer_updated",
            {"consumer_id": str(original.consumer_id)},
        )
        await _eventually(lambda: _require_consumer_email(cache, "updated@example.com"))
    finally:
        await listener.stop()


async def _exercise_catalog_notification(postgres_engine) -> None:
    repository = PostgresFinTSInstituteRepository(postgres_engine)
    cache = InMemoryFinTSInstituteCache()
    await _seed_institutes(postgres_engine, _institute("87654321"))
    await cache.load([_institute("12345678")])
    listener = _build_listener(
        postgres_engine=postgres_engine,
        institute_repository=repository,
        institute_cache=cache,
    )

    await asyncio.wait_for(listener.start(), timeout=5.0)
    try:
        await _publish_notification(
            postgres_engine,
            "gw.catalog_replaced",
            {"replaced_at": "2026-03-12T12:00:00Z"},
        )
        await _eventually(lambda: _require_institute(cache, BankLeitzahl("87654321")))
    finally:
        await listener.stop()


def _build_listener(
    *,
    postgres_engine,
    consumer_repository=None,
    consumer_cache=None,
    institute_repository=None,
    institute_cache=None,
) -> PostgresNotifyListener:
    return PostgresNotifyListener(
        database_url=postgres_engine.url.render_as_string(hide_password=False),
        consumer_repository=consumer_repository
        or PostgresApiConsumerRepository(postgres_engine),
        consumer_cache=consumer_cache or InMemoryApiConsumerCache(),
        institute_repository=institute_repository
        or PostgresFinTSInstituteRepository(postgres_engine),
        institute_cache=institute_cache or InMemoryFinTSInstituteCache(),
        reconnect_backoff_seconds=0.05,
        max_reconnect_backoff_seconds=0.2,
    )


async def _publish_notification(
    postgres_engine, channel: str, payload: dict[str, str]
) -> None:
    statement = text("SELECT pg_notify(:channel, :payload)")
    async with postgres_engine.begin() as connection:
        await connection.execute(
            statement,
            {"channel": channel, "payload": json.dumps(payload)},
        )


async def _eventually(
    predicate,
    *,
    timeout_seconds: float = 2.0,
    interval_seconds: float = 0.05,
) -> None:
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while True:
        if await predicate():
            return
        if asyncio.get_running_loop().time() >= deadline:
            raise AssertionError("Timed out waiting for notification handler")
        await asyncio.sleep(interval_seconds)


async def _require_consumer_email(
    cache: InMemoryApiConsumerCache, expected_email: str
) -> bool:
    consumers = await cache.list_active()
    return consumers == [_consumer(expected_email)]


async def _require_institute(
    cache: InMemoryFinTSInstituteCache, blz: BankLeitzahl
) -> bool:
    return await cache.get_by_blz(blz) == _institute(str(blz))


def _consumer(email: str, *, consumer_id: UUID | None = None) -> ApiConsumer:
    return ApiConsumer(
        consumer_id=consumer_id or UUID("12345678-1234-5678-1234-567812345678"),
        email=email,
        api_key_hash=ApiKeyHash("hash-1"),
        status=ConsumerStatus.ACTIVE,
        created_at=datetime(2026, 3, 7, 12, 0, tzinfo=UTC),
    )


def _institute(blz: str) -> FinTSInstitute:
    return FinTSInstitute(
        blz=BankLeitzahl(blz),
        bic="GENODEF1ABC",
        name=f"Bank {blz}",
        city="Berlin",
        organization="Example Org",
        pin_tan_url="https://bank.example/fints",
        fints_version="FinTS V3.0",
        last_source_update=date(2026, 3, 7),
        source_row_checksum=f"checksum-{blz}",
        source_payload={"blz": blz},
    )
