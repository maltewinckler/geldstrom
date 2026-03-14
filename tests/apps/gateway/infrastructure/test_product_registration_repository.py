"""Integration tests for the PostgreSQL product registration repository."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from gateway.domain.product_registration import (
    EncryptedProductKey,
    FinTSProductRegistration,
    KeyVersion,
    ProductVersion,
)
from gateway.domain.shared import EntityId
from gateway.infrastructure.persistence.postgres import (
    PostgresFinTSProductRegistrationRepository,
)


def test_product_registration_repository_save_and_get_current(
    postgres_engine, async_runner
) -> None:
    repository = PostgresFinTSProductRegistrationRepository(postgres_engine)
    registration = _registration(
        "11111111-1111-1111-1111-111111111111", b"encrypted-1"
    )

    async_runner(repository.save_current(registration))

    loaded = async_runner(repository.get_current())

    assert loaded == registration


def test_product_registration_repository_updates_current(
    postgres_engine, async_runner
) -> None:
    repository = PostgresFinTSProductRegistrationRepository(postgres_engine)
    first = _registration("11111111-1111-1111-1111-111111111111", b"encrypted-1")
    second = _registration("22222222-2222-2222-2222-222222222222", b"encrypted-2")

    async_runner(repository.save_current(first))
    async_runner(repository.save_current(second))

    loaded = async_runner(repository.get_current())

    assert loaded == second


def _registration(
    registration_id: str, encrypted_key: bytes
) -> FinTSProductRegistration:
    return FinTSProductRegistration(
        registration_id=EntityId(UUID(registration_id)),
        encrypted_product_key=EncryptedProductKey(encrypted_key),
        product_version=ProductVersion("1.0.0"),
        key_version=KeyVersion("v1"),
        updated_at=datetime(2026, 3, 7, 12, 0, tzinfo=UTC),
    )
