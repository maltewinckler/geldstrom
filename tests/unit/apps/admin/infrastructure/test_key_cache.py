"""Unit tests for the InMemoryKeyCache.

Tests:
- get/set/delete/load_all operations
"""

from uuid import uuid4

import pytest

from admin.domain.api_keys.value_objects.sha256_key_hash import SHA256KeyHash
from admin.infrastructure.cache.key_cache import InMemoryKeyCache


class TestInMemoryKeyCache:
    """Tests for InMemoryKeyCache."""

    @pytest.fixture
    def cache(self) -> InMemoryKeyCache:
        """Create an InMemoryKeyCache instance."""
        return InMemoryKeyCache()

    @pytest.fixture
    def sha256_hash(self) -> SHA256KeyHash:
        """Create a sample SHA256KeyHash."""
        return SHA256KeyHash(value="a" * 64)

    @pytest.fixture
    def account_id(self):
        """Create a sample account ID."""
        return uuid4()

    @pytest.mark.asyncio
    async def test_get_returns_none_for_missing_key(
        self, cache: InMemoryKeyCache, sha256_hash: SHA256KeyHash
    ) -> None:
        """get() should return None for a key not in cache."""
        result = await cache.get(sha256_hash)

        assert result is None

    @pytest.mark.asyncio
    async def test_set_then_get_returns_account_id(
        self, cache: InMemoryKeyCache, sha256_hash: SHA256KeyHash, account_id
    ) -> None:
        """set() then get() should return the account_id."""
        await cache.set(sha256_hash, account_id)

        result = await cache.get(sha256_hash)

        assert result == str(account_id)

    @pytest.mark.asyncio
    async def test_delete_removes_key(
        self, cache: InMemoryKeyCache, sha256_hash: SHA256KeyHash, account_id
    ) -> None:
        """delete() should remove the key from cache."""
        await cache.set(sha256_hash, account_id)
        await cache.delete(sha256_hash)

        result = await cache.get(sha256_hash)

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key_does_not_raise(
        self, cache: InMemoryKeyCache, sha256_hash: SHA256KeyHash
    ) -> None:
        """delete() should not raise for a key not in cache."""
        # Should not raise
        await cache.delete(sha256_hash)

    @pytest.mark.asyncio
    async def test_load_all_populates_cache(self, cache: InMemoryKeyCache) -> None:
        """load_all() should populate the cache with all provided keys."""
        keys = [
            (SHA256KeyHash(value="a" * 64), uuid4()),
            (SHA256KeyHash(value="b" * 64), uuid4()),
            (SHA256KeyHash(value="c" * 64), uuid4()),
        ]

        await cache.load_all(keys)

        for sha256_hash, account_id in keys:
            result = await cache.get(sha256_hash)
            assert result == str(account_id)

    @pytest.mark.asyncio
    async def test_load_all_with_empty_list(self, cache: InMemoryKeyCache) -> None:
        """load_all() with empty list should not raise."""
        await cache.load_all([])

        # Cache should still be empty
        result = await cache.get(SHA256KeyHash(value="a" * 64))
        assert result is None

    @pytest.mark.asyncio
    async def test_set_overwrites_existing_value(
        self, cache: InMemoryKeyCache, sha256_hash: SHA256KeyHash
    ) -> None:
        """set() should overwrite an existing value."""
        account_id1 = uuid4()
        account_id2 = uuid4()

        await cache.set(sha256_hash, account_id1)
        await cache.set(sha256_hash, account_id2)

        result = await cache.get(sha256_hash)

        assert result == str(account_id2)

    @pytest.mark.asyncio
    async def test_multiple_keys_independent(self, cache: InMemoryKeyCache) -> None:
        """Multiple keys should be stored independently."""
        hash1 = SHA256KeyHash(value="a" * 64)
        hash2 = SHA256KeyHash(value="b" * 64)
        account_id1 = uuid4()
        account_id2 = uuid4()

        await cache.set(hash1, account_id1)
        await cache.set(hash2, account_id2)

        assert await cache.get(hash1) == str(account_id1)
        assert await cache.get(hash2) == str(account_id2)

        # Deleting one should not affect the other
        await cache.delete(hash1)
        assert await cache.get(hash1) is None
        assert await cache.get(hash2) == str(account_id2)
