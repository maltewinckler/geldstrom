"""Tests for the in-memory current product key provider."""

from __future__ import annotations

import asyncio

import pytest

from gateway.application.common import InternalError
from gateway.infrastructure.cache.memory import InMemoryCurrentProductKeyProvider


def test_in_memory_current_product_key_provider_returns_loaded_key() -> None:
    provider = InMemoryCurrentProductKeyProvider("product-key-1")

    result = asyncio.run(provider.require_current())

    assert result == "product-key-1"


def test_in_memory_current_product_key_provider_raises_when_missing() -> None:
    provider = InMemoryCurrentProductKeyProvider()

    with pytest.raises(InternalError, match="No current product key is loaded"):
        asyncio.run(provider.require_current())


def test_in_memory_current_product_key_provider_returns_reloaded_key() -> None:
    provider = InMemoryCurrentProductKeyProvider("product-key-1")

    asyncio.run(provider.load_current("product-key-2"))
    result = asyncio.run(provider.require_current())

    assert result == "product-key-2"
