"""Unit tests for the api_keys domain layer.

Tests:
- RawKey.generate() produces 64-char hex
- SHA256KeyHash.from_raw_key() determinism
- KeyStatus enum values
"""

import re

import pytest
from pydantic import SecretStr

from admin.domain.api_keys.value_objects.key_status import KeyStatus
from admin.domain.api_keys.value_objects.raw_key import RawKey
from admin.domain.api_keys.value_objects.sha256_key_hash import SHA256KeyHash


class TestRawKey:
    """Tests for RawKey value object."""

    def test_generate_produces_64_char_hex(self) -> None:
        """RawKey.generate() should produce a 64-character lowercase hex string."""
        raw_key = RawKey.generate()
        value = raw_key.value.get_secret_value()

        assert len(value) == 64
        assert re.match(r"^[0-9a-f]{64}$", value) is not None

    def test_generate_produces_unique_values(self) -> None:
        """Two independently generated RawKeys should be distinct."""
        raw_key1 = RawKey.generate()
        raw_key2 = RawKey.generate()

        assert raw_key1.value.get_secret_value() != raw_key2.value.get_secret_value()

    def test_raw_key_is_frozen(self) -> None:
        """RawKey should be immutable (frozen)."""
        raw_key = RawKey.generate()

        with pytest.raises(Exception):  # ValidationError for frozen models
            raw_key.value = SecretStr("new_value")

    def test_raw_key_from_value(self) -> None:
        """RawKey can be constructed from a known value."""
        known_value = "a" * 64
        raw_key = RawKey(value=SecretStr(known_value))

        assert raw_key.value.get_secret_value() == known_value


class TestSHA256KeyHash:
    """Tests for SHA256KeyHash value object."""

    def test_from_raw_key_determinism(self) -> None:
        """SHA256KeyHash.from_raw_key() should be deterministic."""
        raw_key = RawKey(value=SecretStr("a" * 64))

        hash1 = SHA256KeyHash.from_raw_key(raw_key)
        hash2 = SHA256KeyHash.from_raw_key(raw_key)

        assert hash1.value == hash2.value

    def test_from_raw_key_produces_64_char_hex(self) -> None:
        """SHA256KeyHash should be a 64-character hex string (SHA-256 = 256 bits = 64 hex chars)."""
        raw_key = RawKey.generate()
        sha256_hash = SHA256KeyHash.from_raw_key(raw_key)

        assert len(sha256_hash.value) == 64
        assert re.match(r"^[0-9a-f]{64}$", sha256_hash.value) is not None

    def test_different_raw_keys_produce_different_hashes(self) -> None:
        """Different RawKeys should produce different SHA256KeyHashes."""
        raw_key1 = RawKey(value=SecretStr("a" * 64))
        raw_key2 = RawKey(value=SecretStr("b" * 64))

        hash1 = SHA256KeyHash.from_raw_key(raw_key1)
        hash2 = SHA256KeyHash.from_raw_key(raw_key2)

        assert hash1.value != hash2.value

    def test_sha256_key_hash_is_frozen(self) -> None:
        """SHA256KeyHash should be immutable (frozen)."""
        raw_key = RawKey.generate()
        sha256_hash = SHA256KeyHash.from_raw_key(raw_key)

        with pytest.raises(Exception):  # ValidationError for frozen models
            sha256_hash.value = "new_value"


class TestKeyStatus:
    """Tests for KeyStatus enum."""

    def test_has_active_value(self) -> None:
        """KeyStatus should have an 'active' value."""
        assert KeyStatus.active == "active"

    def test_has_revoked_value(self) -> None:
        """KeyStatus should have a 'revoked' value."""
        assert KeyStatus.revoked == "revoked"

    def test_only_two_values(self) -> None:
        """KeyStatus should only have 'active' and 'revoked' values."""
        assert set(KeyStatus) == {KeyStatus.active, KeyStatus.revoked}

    def test_is_str_enum(self) -> None:
        """KeyStatus values should be strings."""
        assert isinstance(KeyStatus.active, str)
        assert isinstance(KeyStatus.revoked, str)
