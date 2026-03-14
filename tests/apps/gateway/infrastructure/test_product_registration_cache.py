"""Tests for the in-memory product registration cache."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from gateway.domain.product_registration import (
    EncryptedProductKey,
    FinTSProductRegistration,
    KeyVersion,
    ProductVersion,
)
from gateway.domain.shared import EntityId
from gateway.infrastructure.cache.memory import InMemoryProductRegistrationCache


def test_product_registration_cache_stores_current_registration() -> None:
    cache = InMemoryProductRegistrationCache()
    registration = _registration(b"encrypted-1")

    asyncio.run(cache.set_current(registration))

    assert asyncio.run(cache.get_current()) == registration


def test_product_registration_cache_replaces_current_registration() -> None:
    cache = InMemoryProductRegistrationCache()
    first = _registration(b"encrypted-1")
    second = _registration(
        b"encrypted-2", registration_id="22222222-2222-2222-2222-222222222222"
    )
    asyncio.run(cache.set_current(first))

    asyncio.run(cache.set_current(second))

    assert asyncio.run(cache.get_current()) == second


def _registration(
    encrypted_key: bytes,
    *,
    registration_id: str = "11111111-1111-1111-1111-111111111111",
) -> FinTSProductRegistration:
    return FinTSProductRegistration(
        registration_id=EntityId(UUID(registration_id)),
        encrypted_product_key=EncryptedProductKey(encrypted_key),
        product_version=ProductVersion("1.0.0"),
        key_version=KeyVersion("v1"),
        updated_at=datetime(2026, 3, 7, 12, 0, tzinfo=UTC),
    )
