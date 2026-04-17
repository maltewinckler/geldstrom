"""Integration tests for the PostgreSQL API consumer repository."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from gateway_contracts.schema import api_consumers_table

from gateway.domain.consumer_access import (
    ApiConsumer,
    ApiKeyHash,
    ConsumerStatus,
)


async def _seed_consumers(engine, *consumers: ApiConsumer) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            api_consumers_table.insert(),
            [
                {
                    "consumer_id": c.consumer_id,
                    "email": c.email,
                    "api_key_hash": c.api_key_hash.value if c.api_key_hash else None,
                    "status": c.status.value,
                    "created_at": c.created_at,
                    "rotated_at": c.rotated_at,
                }
                for c in consumers
            ],
        )


def test_consumer_repository_get_by_id(postgres_engine, async_runner) -> None:
    consumer = _consumer()
    async_runner(_seed_consumers(postgres_engine, consumer))
    repository = ApiConsumerRepositorySqlAlchemy(postgres_engine)

    loaded = async_runner(repository.get_by_id(consumer.consumer_id))

    assert loaded == consumer


def test_consumer_repository_get_by_id_returns_none_for_unknown(
    postgres_engine, async_runner
) -> None:
    repository = ApiConsumerRepositorySqlAlchemy(postgres_engine)

    result = async_runner(
        repository.get_by_id(UUID("00000000-0000-0000-0000-000000000000"))
    )

    assert result is None


def test_consumer_repository_get_by_email(postgres_engine, async_runner) -> None:
    consumer = _consumer()
    async_runner(_seed_consumers(postgres_engine, consumer))
    repository = ApiConsumerRepositorySqlAlchemy(postgres_engine)

    loaded = async_runner(repository.get_by_email(consumer.email))

    assert loaded == consumer


def test_consumer_repository_lists_active(postgres_engine, async_runner) -> None:
    active = _consumer()
    disabled = ApiConsumer(
        consumer_id=UUID("87654321-4321-8765-4321-876543218765"),
        email="disabled@example.com",
        api_key_hash=None,
        status=ConsumerStatus.DISABLED,
        created_at=datetime(2026, 3, 7, 12, 0, tzinfo=UTC),
    )
    async_runner(_seed_consumers(postgres_engine, active, disabled))
    repository = ApiConsumerRepositorySqlAlchemy(postgres_engine)

    loaded = async_runner(repository.list_all_active())

    assert loaded == [active]


def test_consumer_repository_lists_all_consumers(postgres_engine, async_runner) -> None:
    active = _consumer()
    disabled = ApiConsumer(
        consumer_id=UUID("87654321-4321-8765-4321-876543218765"),
        email="disabled@example.com",
        api_key_hash=None,
        status=ConsumerStatus.DISABLED,
        created_at=datetime(2026, 3, 7, 12, 0, tzinfo=UTC),
    )
    async_runner(_seed_consumers(postgres_engine, active, disabled))
    repository = ApiConsumerRepositorySqlAlchemy(postgres_engine)

    loaded = async_runner(repository.list_all())

    assert loaded == [active, disabled]


def _consumer() -> ApiConsumer:
    return ApiConsumer(
        consumer_id=UUID("12345678-1234-5678-1234-567812345678"),
        email="consumer@example.com",
        api_key_hash=ApiKeyHash("hash-1"),
        status=ConsumerStatus.ACTIVE,
        created_at=datetime(2026, 3, 7, 12, 0, tzinfo=UTC),
    )
