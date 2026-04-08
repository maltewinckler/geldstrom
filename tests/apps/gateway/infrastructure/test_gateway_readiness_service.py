"""Integration tests for SQLGatewayReadinessService against a real PostgreSQL DB."""

from __future__ import annotations

from datetime import UTC, datetime

import fakeredis.aioredis
from gateway_contracts.schema import (
    fints_institutes_table,
    fints_product_registration_table,
)

from gateway.infrastructure.readiness import SQLGatewayReadinessService


def _make_service(engine):
    redis = fakeredis.aioredis.FakeRedis()
    return SQLGatewayReadinessService(engine, redis)


def test_readiness_service_db_ok_but_empty_on_fresh_schema(
    postgres_engine, async_runner
) -> None:
    service = _make_service(postgres_engine)
    result = async_runner(service.check())

    assert result.db is True
    assert result.product_key is False
    assert result.catalog is False
    assert result.redis is True
    assert result.is_ready is False


def test_readiness_service_product_key_true_after_insert(
    postgres_engine, async_runner
) -> None:
    async_runner(
        _seed_product_key(
            postgres_engine, product_key="test-key", product_version="1.0.0"
        )
    )
    service = _make_service(postgres_engine)
    result = async_runner(service.check())

    assert result.db is True
    assert result.product_key is True
    assert result.catalog is False
    assert result.redis is True
    assert result.is_ready is False


def test_readiness_service_catalog_true_after_insert(
    postgres_engine, async_runner
) -> None:
    async_runner(_seed_institute(postgres_engine))
    service = _make_service(postgres_engine)
    result = async_runner(service.check())

    assert result.db is True
    assert result.product_key is False
    assert result.catalog is True
    assert result.redis is True
    assert result.is_ready is False


def test_readiness_service_fully_ready_when_all_data_present(
    postgres_engine, async_runner
) -> None:
    async_runner(
        _seed_product_key(
            postgres_engine, product_key="test-key", product_version="1.0.0"
        )
    )
    async_runner(_seed_institute(postgres_engine))
    service = _make_service(postgres_engine)
    result = async_runner(service.check())

    assert result.is_ready is True
    assert result.db is True
    assert result.product_key is True
    assert result.catalog is True
    assert result.redis is True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_product_key(engine, *, product_key: str, product_version: str) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            fints_product_registration_table.insert().values(
                singleton_key=True,
                product_key=product_key,
                product_version=product_version,
                updated_at=datetime.now(UTC),
            )
        )


async def _seed_institute(engine) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            fints_institutes_table.insert().values(
                blz="12345678",
                bic="GENODEF1ABC",
                name="Test Bank",
                city="Berlin",
                organization="Test Org",
                pin_tan_url="https://bank.example/fints",
                fints_version="3.0",
                last_source_update=None,
                source_row_checksum="seeded",
                source_payload={},
            )
        )
