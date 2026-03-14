"""Integration tests for PostgreSQL cache invalidation listeners."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import text

from gateway.domain.consumer_access import (
    ApiConsumer,
    ApiKeyHash,
    ConsumerId,
    ConsumerStatus,
    EmailAddress,
)
from gateway.domain.institution_catalog import (
    BankLeitzahl,
    Bic,
    FinTSInstitute,
    InstituteEndpoint,
)
from gateway.domain.product_registration import (
    EncryptedProductKey,
    FinTSProductRegistration,
    KeyVersion,
    ProductVersion,
)
from gateway.domain.shared import EntityId
from gateway.infrastructure.cache.memory import (
    InMemoryApiConsumerCache,
    InMemoryFinTSInstituteCache,
    InMemoryProductRegistrationCache,
    PostgresNotifyListener,
)
from gateway.infrastructure.persistence.postgres import (
    PostgresApiConsumerRepository,
    PostgresFinTSInstituteRepository,
    PostgresFinTSProductRegistrationRepository,
)


def test_notify_listener_refreshes_one_consumer(postgres_engine, async_runner) -> None:
    async_runner(_exercise_consumer_notification(postgres_engine))


def test_notify_listener_reloads_catalog(postgres_engine, async_runner) -> None:
    async_runner(_exercise_catalog_notification(postgres_engine))


def test_notify_listener_refreshes_product_registration(
    postgres_engine, async_runner
) -> None:
    async_runner(_exercise_product_registration_notification(postgres_engine))


async def _exercise_consumer_notification(postgres_engine) -> None:
    repository = PostgresApiConsumerRepository(postgres_engine)
    cache = InMemoryApiConsumerCache()
    original = _consumer("consumer@example.com")
    updated = _consumer("updated@example.com", consumer_id=original.consumer_id)
    await repository.save(updated)
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
        await _eventually(
            lambda: _require_consumer_email(cache, EmailAddress("updated@example.com"))
        )
    finally:
        await listener.stop()


async def _exercise_catalog_notification(postgres_engine) -> None:
    repository = PostgresFinTSInstituteRepository(postgres_engine)
    cache = InMemoryFinTSInstituteCache()
    await repository.replace_catalog([_institute("87654321")])
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
        await _eventually(
            lambda: _require_institute(cache, BankLeitzahl("87654321"))
        )
    finally:
        await listener.stop()


async def _exercise_product_registration_notification(postgres_engine) -> None:
    repository = PostgresFinTSProductRegistrationRepository(postgres_engine)
    cache = InMemoryProductRegistrationCache()
    registration = _registration(
        "22222222-2222-2222-2222-222222222222", b"encrypted-2"
    )
    await repository.save_current(registration)
    await cache.set_current(_registration("11111111-1111-1111-1111-111111111111", b"encrypted-1"))
    listener = _build_listener(
        postgres_engine=postgres_engine,
        product_registration_repository=repository,
        product_registration_cache=cache,
    )

    await asyncio.wait_for(listener.start(), timeout=5.0)
    try:
        await _publish_notification(
            postgres_engine,
            "gw.product_registration_updated",
            {"registration_id": str(registration.registration_id)},
        )
        await _eventually(lambda: _require_registration(cache, registration))
    finally:
        await listener.stop()


def _build_listener(
    *,
    postgres_engine,
    consumer_repository=None,
    consumer_cache=None,
    institute_repository=None,
    institute_cache=None,
    product_registration_repository=None,
    product_registration_cache=None,
) -> PostgresNotifyListener:
    return PostgresNotifyListener(
        database_url=postgres_engine.url.render_as_string(hide_password=False),
        consumer_repository=consumer_repository
        or PostgresApiConsumerRepository(postgres_engine),
        consumer_cache=consumer_cache or InMemoryApiConsumerCache(),
        institute_repository=institute_repository
        or PostgresFinTSInstituteRepository(postgres_engine),
        institute_cache=institute_cache or InMemoryFinTSInstituteCache(),
        product_registration_repository=product_registration_repository
        or PostgresFinTSProductRegistrationRepository(postgres_engine),
        product_registration_cache=(
            product_registration_cache or InMemoryProductRegistrationCache()
        ),
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
    cache: InMemoryApiConsumerCache, expected_email: EmailAddress
) -> bool:
    consumers = await cache.list_active()
    return consumers == [_consumer(expected_email.value)]


async def _require_institute(
    cache: InMemoryFinTSInstituteCache, blz: BankLeitzahl
) -> bool:
    return await cache.get_by_blz(blz) == _institute(str(blz))


async def _require_registration(
    cache: InMemoryProductRegistrationCache,
    expected: FinTSProductRegistration,
) -> bool:
    return await cache.get_current() == expected


def _consumer(email: str, *, consumer_id: ConsumerId | None = None) -> ApiConsumer:
    return ApiConsumer(
        consumer_id=consumer_id
        or ConsumerId(UUID("12345678-1234-5678-1234-567812345678")),
        email=EmailAddress(email),
        api_key_hash=ApiKeyHash("hash-1"),
        status=ConsumerStatus.ACTIVE,
        created_at=datetime(2026, 3, 7, 12, 0, tzinfo=UTC),
    )


def _institute(blz: str) -> FinTSInstitute:
    return FinTSInstitute(
        blz=BankLeitzahl(blz),
        bic=Bic("GENODEF1ABC"),
        name=f"Bank {blz}",
        city="Berlin",
        organization="Example Org",
        pin_tan_url=InstituteEndpoint("https://bank.example/fints"),
        fints_version="FinTS V3.0",
        last_source_update=date(2026, 3, 7),
        source_row_checksum=f"checksum-{blz}",
        source_payload={"blz": blz},
    )


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
