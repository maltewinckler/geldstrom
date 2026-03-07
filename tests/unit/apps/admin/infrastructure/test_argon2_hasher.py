"""Unit tests for the Argon2idKeyHasher.

Tests:
- hash() and verify() round-trip
"""

import pytest
from pydantic import SecretStr

from admin.domain.api_keys.value_objects.key_hash import KeyHash
from admin.domain.api_keys.value_objects.raw_key import RawKey
from admin.infrastructure.hashing.argon2_hasher import Argon2idKeyHasher


class TestArgon2idKeyHasher:
    """Tests for Argon2idKeyHasher."""

    @pytest.fixture
    def hasher(self) -> Argon2idKeyHasher:
        """Create an Argon2idKeyHasher instance."""
        return Argon2idKeyHasher()

    @pytest.mark.asyncio
    async def test_hash_produces_argon2id_hash(self, hasher: Argon2idKeyHasher) -> None:
        """hash() should produce an Argon2id hash string."""
        raw_key = RawKey.generate()

        key_hash = await hasher.hash(raw_key)

        assert isinstance(key_hash, KeyHash)
        assert key_hash.value.startswith("$argon2id$")

    @pytest.mark.asyncio
    async def test_hash_verify_round_trip(self, hasher: Argon2idKeyHasher) -> None:
        """hash() then verify() should return True for the same raw key."""
        raw_key = RawKey.generate()

        key_hash = await hasher.hash(raw_key)
        is_valid = await hasher.verify(raw_key, key_hash)

        assert is_valid is True

    @pytest.mark.asyncio
    async def test_verify_returns_false_for_wrong_key(
        self, hasher: Argon2idKeyHasher
    ) -> None:
        """verify() should return False for a different raw key."""
        raw_key1 = RawKey.generate()
        raw_key2 = RawKey.generate()

        key_hash = await hasher.hash(raw_key1)
        is_valid = await hasher.verify(raw_key2, key_hash)

        assert is_valid is False

    @pytest.mark.asyncio
    async def test_verify_returns_false_for_invalid_hash(
        self, hasher: Argon2idKeyHasher
    ) -> None:
        """verify() should return False for an invalid hash."""
        raw_key = RawKey.generate()
        invalid_hash = KeyHash(value="invalid_hash_value")

        is_valid = await hasher.verify(raw_key, invalid_hash)

        assert is_valid is False

    @pytest.mark.asyncio
    async def test_hash_is_deterministic_per_call(
        self, hasher: Argon2idKeyHasher
    ) -> None:
        """hash() should produce different hashes for the same key (due to salt)."""
        raw_key = RawKey(value=SecretStr("a" * 64))

        hash1 = await hasher.hash(raw_key)
        hash2 = await hasher.hash(raw_key)

        # Argon2 uses random salt, so hashes should be different
        assert hash1.value != hash2.value

    @pytest.mark.asyncio
    async def test_verify_works_with_different_hash_of_same_key(
        self, hasher: Argon2idKeyHasher
    ) -> None:
        """verify() should work with any valid hash of the same key."""
        raw_key = RawKey(value=SecretStr("a" * 64))

        hash1 = await hasher.hash(raw_key)
        hash2 = await hasher.hash(raw_key)

        # Both hashes should verify against the same key
        assert await hasher.verify(raw_key, hash1) is True
        assert await hasher.verify(raw_key, hash2) is True
