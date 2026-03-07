"""Unit tests for the FernetConfigEncryptor.

Tests:
- encrypt() and decrypt() round-trip
"""

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr

from admin.domain.bank_directory.value_objects.banking_protocol import BankingProtocol
from admin.domain.bank_directory.value_objects.protocol_config import FinTSConfig
from admin.infrastructure.encryption.fernet_encryptor import FernetConfigEncryptor


class TestFernetConfigEncryptor:
    """Tests for FernetConfigEncryptor."""

    @pytest.fixture
    def fernet_key(self) -> bytes:
        """Generate a valid Fernet key."""
        return Fernet.generate_key()

    @pytest.fixture
    def encryptor(self, fernet_key: bytes) -> FernetConfigEncryptor:
        """Create a FernetConfigEncryptor instance."""
        return FernetConfigEncryptor(key=fernet_key)

    @pytest.fixture
    def fints_config(self) -> FinTSConfig:
        """Create a sample FinTSConfig."""
        return FinTSConfig(
            product_id=SecretStr("test_product_id"),
            product_version="1.0.0",
            country_code="DE",
        )

    def test_encrypt_produces_bytes(
        self, encryptor: FernetConfigEncryptor, fints_config: FinTSConfig
    ) -> None:
        """encrypt() should produce bytes."""
        encrypted = encryptor.encrypt(fints_config)

        assert isinstance(encrypted, bytes)
        assert len(encrypted) > 0

    def test_encrypt_decrypt_round_trip(
        self, encryptor: FernetConfigEncryptor, fints_config: FinTSConfig
    ) -> None:
        """encrypt() then decrypt() should return the original config."""
        encrypted = encryptor.encrypt(fints_config)
        decrypted = encryptor.decrypt(encrypted, BankingProtocol.fints)

        assert isinstance(decrypted, FinTSConfig)
        assert (
            decrypted.product_id.get_secret_value()
            == fints_config.product_id.get_secret_value()
        )
        assert decrypted.product_version == fints_config.product_version
        assert decrypted.country_code == fints_config.country_code

    def test_encrypt_produces_different_ciphertext_each_time(
        self, encryptor: FernetConfigEncryptor, fints_config: FinTSConfig
    ) -> None:
        """encrypt() should produce different ciphertext each time (due to IV)."""
        encrypted1 = encryptor.encrypt(fints_config)
        encrypted2 = encryptor.encrypt(fints_config)

        # Fernet uses random IV, so ciphertexts should be different
        assert encrypted1 != encrypted2

    def test_decrypt_with_different_key_fails(self, fints_config: FinTSConfig) -> None:
        """decrypt() should fail with a different key."""
        key1 = Fernet.generate_key()
        key2 = Fernet.generate_key()
        encryptor1 = FernetConfigEncryptor(key=key1)
        encryptor2 = FernetConfigEncryptor(key=key2)

        encrypted = encryptor1.encrypt(fints_config)

        with pytest.raises(Exception):  # InvalidToken
            encryptor2.decrypt(encrypted, BankingProtocol.fints)

    def test_decrypt_unknown_protocol_raises_error(
        self, encryptor: FernetConfigEncryptor, fints_config: FinTSConfig
    ) -> None:
        """decrypt() should raise ValueError for unknown protocol."""
        encrypted = encryptor.encrypt(fints_config)

        # Create a fake protocol value
        with pytest.raises(ValueError, match="Unknown protocol"):
            encryptor.decrypt(encrypted, "unknown_protocol")  # type: ignore

    def test_encrypt_unknown_config_type_raises_error(
        self, encryptor: FernetConfigEncryptor
    ) -> None:
        """encrypt() should raise ValueError for unknown config type."""

        class UnknownConfig:
            pass

        with pytest.raises(ValueError, match="Unknown config type"):
            encryptor.encrypt(UnknownConfig())  # type: ignore

    def test_round_trip_preserves_special_characters(
        self, encryptor: FernetConfigEncryptor
    ) -> None:
        """encrypt/decrypt should preserve special characters in config."""
        config = FinTSConfig(
            product_id=SecretStr("test!@#$%^&*()_+-=[]{}|;':\",./<>?"),
            product_version="1.0.0-beta+build.123",
            country_code="DE",
        )

        encrypted = encryptor.encrypt(config)
        decrypted = encryptor.decrypt(encrypted, BankingProtocol.fints)

        assert (
            decrypted.product_id.get_secret_value()
            == config.product_id.get_secret_value()
        )
        assert decrypted.product_version == config.product_version
