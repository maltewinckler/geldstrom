"""Unit tests for the bank_directory domain layer.

Tests:
- BankEndpoint frozen model
- FinTSConfig validation
- BankingProtocol enum
"""

import pytest
from pydantic import SecretStr, ValidationError

from admin.domain.bank_directory.entities.bank_endpoint import BankEndpoint
from admin.domain.bank_directory.value_objects.banking_protocol import BankingProtocol
from admin.domain.bank_directory.value_objects.protocol_config import FinTSConfig


class TestBankingProtocol:
    """Tests for BankingProtocol enum."""

    def test_has_fints_value(self) -> None:
        """BankingProtocol should have a 'fints' value."""
        assert BankingProtocol.fints == "fints"

    def test_is_str_enum(self) -> None:
        """BankingProtocol values should be strings."""
        assert isinstance(BankingProtocol.fints, str)


class TestFinTSConfig:
    """Tests for FinTSConfig value object."""

    def test_valid_config(self) -> None:
        """FinTSConfig should accept valid configuration."""
        config = FinTSConfig(
            product_id=SecretStr("test_product_id"),
            product_version="1.0.0",
            country_code="DE",
        )

        assert config.product_id.get_secret_value() == "test_product_id"
        assert config.product_version == "1.0.0"
        assert config.country_code == "DE"

    def test_default_country_code(self) -> None:
        """FinTSConfig should default country_code to 'DE'."""
        config = FinTSConfig(
            product_id=SecretStr("test_product_id"),
            product_version="1.0.0",
        )

        assert config.country_code == "DE"

    def test_requires_product_id(self) -> None:
        """FinTSConfig should require product_id."""
        with pytest.raises(ValidationError):
            FinTSConfig(
                product_version="1.0.0",
                country_code="DE",
            )

    def test_requires_product_version(self) -> None:
        """FinTSConfig should require product_version."""
        with pytest.raises(ValidationError):
            FinTSConfig(
                product_id=SecretStr("test_product_id"),
                country_code="DE",
            )

    def test_is_frozen(self) -> None:
        """FinTSConfig should be immutable (frozen)."""
        config = FinTSConfig(
            product_id=SecretStr("test_product_id"),
            product_version="1.0.0",
        )

        with pytest.raises(Exception):  # ValidationError for frozen models
            config.product_version = "2.0.0"


class TestBankEndpoint:
    """Tests for BankEndpoint entity."""

    @pytest.fixture
    def valid_config(self) -> FinTSConfig:
        """Create a valid FinTSConfig for testing."""
        return FinTSConfig(
            product_id=SecretStr("test_product_id"),
            product_version="1.0.0",
            country_code="DE",
        )

    def test_valid_endpoint(self, valid_config: FinTSConfig) -> None:
        """BankEndpoint should accept valid configuration."""
        endpoint = BankEndpoint(
            bank_code="12345678",
            protocol=BankingProtocol.fints,
            server_url="https://banking.example.com/fints",
            protocol_config=valid_config,
            metadata={"name": "Test Bank"},
        )

        assert endpoint.bank_code == "12345678"
        assert endpoint.protocol == BankingProtocol.fints
        assert endpoint.server_url == "https://banking.example.com/fints"
        assert endpoint.protocol_config == valid_config
        assert endpoint.metadata == {"name": "Test Bank"}

    def test_metadata_optional(self, valid_config: FinTSConfig) -> None:
        """BankEndpoint metadata should be optional."""
        endpoint = BankEndpoint(
            bank_code="12345678",
            protocol=BankingProtocol.fints,
            server_url="https://banking.example.com/fints",
            protocol_config=valid_config,
        )

        assert endpoint.metadata is None

    def test_is_frozen(self, valid_config: FinTSConfig) -> None:
        """BankEndpoint should be immutable (frozen)."""
        endpoint = BankEndpoint(
            bank_code="12345678",
            protocol=BankingProtocol.fints,
            server_url="https://banking.example.com/fints",
            protocol_config=valid_config,
        )

        with pytest.raises(Exception):  # ValidationError for frozen models
            endpoint.bank_code = "87654321"

    def test_requires_bank_code(self, valid_config: FinTSConfig) -> None:
        """BankEndpoint should require bank_code."""
        with pytest.raises(ValidationError):
            BankEndpoint(
                protocol=BankingProtocol.fints,
                server_url="https://banking.example.com/fints",
                protocol_config=valid_config,
            )

    def test_requires_protocol(self, valid_config: FinTSConfig) -> None:
        """BankEndpoint should require protocol."""
        with pytest.raises(ValidationError):
            BankEndpoint(
                bank_code="12345678",
                server_url="https://banking.example.com/fints",
                protocol_config=valid_config,
            )

    def test_requires_server_url(self, valid_config: FinTSConfig) -> None:
        """BankEndpoint should require server_url."""
        with pytest.raises(ValidationError):
            BankEndpoint(
                bank_code="12345678",
                protocol=BankingProtocol.fints,
                protocol_config=valid_config,
            )

    def test_requires_protocol_config(self) -> None:
        """BankEndpoint should require protocol_config."""
        with pytest.raises(ValidationError):
            BankEndpoint(
                bank_code="12345678",
                protocol=BankingProtocol.fints,
                server_url="https://banking.example.com/fints",
            )
