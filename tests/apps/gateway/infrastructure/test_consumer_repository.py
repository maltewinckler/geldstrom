"""Integration tests for the PostgreSQL API consumer repository."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from gateway.domain.consumer_access import (
    ApiConsumer,
    ApiKeyHash,
    ConsumerId,
    ConsumerStatus,
    EmailAddress,
)
from gateway.infrastructure.persistence.postgres import PostgresApiConsumerRepository


def test_consumer_repository_save_and_load(postgres_engine, async_runner) -> None:
    repository = PostgresApiConsumerRepository(postgres_engine)
    consumer = _consumer()

    async_runner(repository.save(consumer))

    loaded = async_runner(repository.get_by_id(consumer.consumer_id))

    assert loaded == consumer


def test_consumer_repository_lists_active(postgres_engine, async_runner) -> None:
    repository = PostgresApiConsumerRepository(postgres_engine)
    active = _consumer()
    disabled = ApiConsumer(
        consumer_id=ConsumerId(UUID("87654321-4321-8765-4321-876543218765")),
        email=EmailAddress("disabled@example.com"),
        api_key_hash=None,
        status=ConsumerStatus.DISABLED,
        created_at=datetime(2026, 3, 7, 12, 0, tzinfo=UTC),
    )

    async_runner(repository.save(active))
    async_runner(repository.save(disabled))

    loaded = async_runner(repository.list_all_active())

    assert loaded == [active]


def test_consumer_repository_updates_existing_consumer(
    postgres_engine, async_runner
) -> None:
    repository = PostgresApiConsumerRepository(postgres_engine)
    consumer = _consumer()
    async_runner(repository.save(consumer))
    updated = ApiConsumer(
        consumer_id=consumer.consumer_id,
        email=EmailAddress("updated@example.com"),
        api_key_hash=ApiKeyHash("new-hash"),
        status=ConsumerStatus.ACTIVE,
        created_at=consumer.created_at,
        rotated_at=datetime(2026, 3, 7, 13, 0, tzinfo=UTC),
    )

    async_runner(repository.save(updated))

    loaded = async_runner(repository.get_by_email(updated.email))

    assert loaded == updated


def test_consumer_repository_lists_all_consumers(postgres_engine, async_runner) -> None:
    repository = PostgresApiConsumerRepository(postgres_engine)
    active = _consumer()
    disabled = ApiConsumer(
        consumer_id=ConsumerId(UUID("87654321-4321-8765-4321-876543218765")),
        email=EmailAddress("disabled@example.com"),
        api_key_hash=None,
        status=ConsumerStatus.DISABLED,
        created_at=datetime(2026, 3, 7, 12, 0, tzinfo=UTC),
    )

    async_runner(repository.save(active))
    async_runner(repository.save(disabled))

    loaded = async_runner(repository.list_all())

    assert loaded == [active, disabled]


def _consumer() -> ApiConsumer:
    return ApiConsumer(
        consumer_id=ConsumerId(UUID("12345678-1234-5678-1234-567812345678")),
        email=EmailAddress("consumer@example.com"),
        api_key_hash=ApiKeyHash("hash-1"),
        status=ConsumerStatus.ACTIVE,
        created_at=datetime(2026, 3, 7, 12, 0, tzinfo=UTC),
    )
