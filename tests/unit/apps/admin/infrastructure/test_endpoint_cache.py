"""Unit tests for the InMemoryEndpointCache.

Tests:
- get/set/delete/load_all operations
"""

import pytest
from pydantic import SecretStr

from admin.domain.bank_directory.entities.bank_endpoint import BankEndpoint
from admin.domain.bank_directory.value_objects.banking_protocol import BankingProtocol
from admin.domain.bank_directory.value_objects.protocol_config import FinTSConfig
from admin.infrastructure.cache.endpoint_cache import InMemoryEndpointCache


class TestInMemoryEndpointCache:
    """Tests for InMemoryEndpointCache."""

    @pytest.fixture
    def cache(self) -> InMemoryEndpointCache:
        """Create an InMemoryEndpointCache instance."""
        return InMemoryEndpointCache()

    @pytest.fixture
    def bank_endpoint(self) -> BankEndpoint:
        """Create a sample BankEndpoint."""
        return BankEndpoint(
            bank_code="TEST001",
            protocol=BankingProtocol.fints,
            server_url="https://fints.example.com",
            protocol_config=FinTSConfig(
                product_id=SecretStr("test_product_id"),
                product_version="1.0.0",
                country_code="DE",
            ),
            metadata={"key": "value"},
        )

    @pytest.mark.asyncio
    async def test_get_returns_none_for_missing_endpoint(
        self, cache: InMemoryEndpointCache
    ) -> None:
        """get() should return None for an endpoint not in cache."""
        result = await cache.get("NONEXISTENT")

        assert result is None

    @pytest.mark.asyncio
    async def test_set_then_get_returns_endpoint(
        self, cache: InMemoryEndpointCache, bank_endpoint: BankEndpoint
    ) -> None:
        """set() then get() should return the endpoint."""
        await cache.set(bank_endpoint)

        result = await cache.get(bank_endpoint.bank_code)

        assert result is not None
        assert result.bank_code == bank_endpoint.bank_code
        assert result.protocol == bank_endpoint.protocol
        assert result.server_url == bank_endpoint.server_url

    @pytest.mark.asyncio
    async def test_delete_removes_endpoint(
        self, cache: InMemoryEndpointCache, bank_endpoint: BankEndpoint
    ) -> None:
        """delete() should remove the endpoint from cache."""
        await cache.set(bank_endpoint)
        await cache.delete(bank_endpoint.bank_code)

        result = await cache.get(bank_endpoint.bank_code)

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_endpoint_does_not_raise(
        self, cache: InMemoryEndpointCache
    ) -> None:
        """delete() should not raise for an endpoint not in cache."""
        # Should not raise
        await cache.delete("NONEXISTENT")

    @pytest.mark.asyncio
    async def test_load_all_populates_cache(self, cache: InMemoryEndpointCache) -> None:
        """load_all() should populate the cache with all provided endpoints."""
        endpoints = [
            BankEndpoint(
                bank_code=f"BANK{i:03d}",
                protocol=BankingProtocol.fints,
                server_url=f"https://fints{i}.example.com",
                protocol_config=FinTSConfig(
                    product_id=SecretStr(f"product_{i}"),
                    product_version="1.0.0",
                    country_code="DE",
                ),
            )
            for i in range(3)
        ]

        await cache.load_all(endpoints)

        for endpoint in endpoints:
            result = await cache.get(endpoint.bank_code)
            assert result is not None
            assert result.bank_code == endpoint.bank_code

    @pytest.mark.asyncio
    async def test_load_all_with_empty_list(self, cache: InMemoryEndpointCache) -> None:
        """load_all() with empty list should not raise."""
        await cache.load_all([])

        # Cache should still be empty
        result = await cache.get("NONEXISTENT")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_overwrites_existing_endpoint(
        self, cache: InMemoryEndpointCache
    ) -> None:
        """set() should overwrite an existing endpoint."""
        endpoint1 = BankEndpoint(
            bank_code="TEST001",
            protocol=BankingProtocol.fints,
            server_url="https://old.example.com",
            protocol_config=FinTSConfig(
                product_id=SecretStr("old_product"),
                product_version="1.0.0",
                country_code="DE",
            ),
        )
        endpoint2 = BankEndpoint(
            bank_code="TEST001",
            protocol=BankingProtocol.fints,
            server_url="https://new.example.com",
            protocol_config=FinTSConfig(
                product_id=SecretStr("new_product"),
                product_version="2.0.0",
                country_code="DE",
            ),
        )

        await cache.set(endpoint1)
        await cache.set(endpoint2)

        result = await cache.get("TEST001")

        assert result is not None
        assert result.server_url == "https://new.example.com"

    @pytest.mark.asyncio
    async def test_multiple_endpoints_independent(
        self, cache: InMemoryEndpointCache
    ) -> None:
        """Multiple endpoints should be stored independently."""
        endpoint1 = BankEndpoint(
            bank_code="BANK001",
            protocol=BankingProtocol.fints,
            server_url="https://bank1.example.com",
            protocol_config=FinTSConfig(
                product_id=SecretStr("product_1"),
                product_version="1.0.0",
                country_code="DE",
            ),
        )
        endpoint2 = BankEndpoint(
            bank_code="BANK002",
            protocol=BankingProtocol.fints,
            server_url="https://bank2.example.com",
            protocol_config=FinTSConfig(
                product_id=SecretStr("product_2"),
                product_version="1.0.0",
                country_code="DE",
            ),
        )

        await cache.set(endpoint1)
        await cache.set(endpoint2)

        assert (await cache.get("BANK001")).bank_code == "BANK001"
        assert (await cache.get("BANK002")).bank_code == "BANK002"

        # Deleting one should not affect the other
        await cache.delete("BANK001")
        assert await cache.get("BANK001") is None
        assert (await cache.get("BANK002")).bank_code == "BANK002"
