"""Integration tests for PostgreSQL cache invalidation listeners."""

from __future__ import annotations

import asyncio
import json
from datetime import date

from gateway_contracts.schema import fints_institutes_table
from sqlalchemy import text

from gateway.domain.banking_gateway import (
    BankLeitzahl,
    FinTSInstitute,
)
from gateway.infrastructure.cache.memory import (
    InMemoryFinTSInstituteCache,
    PostgresNotifyListener,
)
from gateway.infrastructure.persistence.sqlalchemy import (
    FinTSInstituteRepositorySqlAlchemy,
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
                    "source_row_checksum": "seeded",
                    "source_payload": {},
                }
                for inst in institutes
            ],
        )


def test_notify_listener_reloads_catalog(postgres_engine, async_runner) -> None:
    async_runner(_exercise_catalog_notification(postgres_engine))


async def _exercise_catalog_notification(postgres_engine) -> None:
    repository = FinTSInstituteRepositorySqlAlchemy(postgres_engine)
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
    institute_repository=None,
    institute_cache=None,
) -> PostgresNotifyListener:
    return PostgresNotifyListener(
        database_url=postgres_engine.url.render_as_string(hide_password=False),
        institute_repository=institute_repository
        or FinTSInstituteRepositorySqlAlchemy(postgres_engine),
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


async def _require_institute(
    cache: InMemoryFinTSInstituteCache, blz: BankLeitzahl
) -> bool:
    return await cache.get_by_blz(blz) == _institute(str(blz))


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
    )
