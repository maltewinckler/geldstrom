"""Unit tests for the gRPC servicers.

Tests:
- KeyValidationServicer with mock caches and repos
- BankDirectoryServicer with mock caches and repos
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from grpc import StatusCode
from pydantic import SecretStr
from sqlalchemy.exc import SQLAlchemyError

from admin.domain.api_keys.entities.api_key import ApiKey
from admin.domain.api_keys.value_objects.key_hash import KeyHash
from admin.domain.api_keys.value_objects.key_status import KeyStatus
from admin.domain.api_keys.value_objects.sha256_key_hash import SHA256KeyHash
from admin.domain.bank_directory.entities.bank_endpoint import BankEndpoint
from admin.domain.bank_directory.value_objects.banking_protocol import BankingProtocol
from admin.domain.bank_directory.value_objects.protocol_config import FinTSConfig
from admin.infrastructure.grpc.bank_directory_servicer import BankDirectoryServicer
from admin.infrastructure.grpc.generated.bank_directory_pb2 import (
    GetBankEndpointRequest,
)
from admin.infrastructure.grpc.generated.key_validation_pb2 import KeyRequest
from admin.infrastructure.grpc.key_validation_servicer import KeyValidationServicer


class TestKeyValidationServicer:
    """Tests for KeyValidationServicer."""

    @pytest.fixture
    def mock_key_cache(self) -> AsyncMock:
        """Create a mock KeyCache."""
        return AsyncMock()

    @pytest.fixture
    def mock_api_key_repo(self) -> AsyncMock:
        """Create a mock ApiKeyRepository."""
        return AsyncMock()

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        """Create a mock gRPC context."""
        context = MagicMock()
        context.abort = AsyncMock()
        return context

    @pytest.fixture
    def servicer(
        self, mock_key_cache: AsyncMock, mock_api_key_repo: AsyncMock
    ) -> KeyValidationServicer:
        """Create a KeyValidationServicer with mock dependencies."""
        return KeyValidationServicer(
            key_cache=mock_key_cache,
            api_key_repo=mock_api_key_repo,
        )

    @pytest.fixture
    def active_api_key(self) -> ApiKey:
        """Create an active API key for testing."""
        return ApiKey(
            id=uuid4(),
            account_id=uuid4(),
            key_hash=KeyHash(value="argon2id_hash_value"),
            sha256_key_hash=SHA256KeyHash(value="a" * 64),
            status=KeyStatus.active,
            created_at=datetime.now(UTC),
        )

    @pytest.mark.asyncio
    async def test_validate_key_cache_hit(
        self,
        servicer: KeyValidationServicer,
        mock_key_cache: AsyncMock,
        mock_context: MagicMock,
    ) -> None:
        """ValidateKey should return valid=True when key is in cache."""
        account_id = str(uuid4())
        mock_key_cache.get.return_value = account_id

        request = KeyRequest(key_hash="a" * 64)
        response = await servicer.ValidateKey(request, mock_context)

        assert response.is_valid is True
        assert response.account_id == account_id
        mock_key_cache.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_key_cache_miss_db_hit(
        self,
        servicer: KeyValidationServicer,
        mock_key_cache: AsyncMock,
        mock_api_key_repo: AsyncMock,
        mock_context: MagicMock,
        active_api_key: ApiKey,
    ) -> None:
        """ValidateKey should fall back to DB and populate cache on cache miss."""
        mock_key_cache.get.return_value = None
        mock_api_key_repo.get_by_sha256_hash.return_value = active_api_key

        request = KeyRequest(key_hash="a" * 64)
        response = await servicer.ValidateKey(request, mock_context)

        assert response.is_valid is True
        assert response.account_id == str(active_api_key.account_id)
        mock_key_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_key_not_found(
        self,
        servicer: KeyValidationServicer,
        mock_key_cache: AsyncMock,
        mock_api_key_repo: AsyncMock,
        mock_context: MagicMock,
    ) -> None:
        """ValidateKey should return valid=False when key not found."""
        mock_key_cache.get.return_value = None
        mock_api_key_repo.get_by_sha256_hash.return_value = None

        request = KeyRequest(key_hash="a" * 64)
        response = await servicer.ValidateKey(request, mock_context)

        assert response.is_valid is False
        assert response.account_id == ""

    @pytest.mark.asyncio
    async def test_validate_key_revoked(
        self,
        servicer: KeyValidationServicer,
        mock_key_cache: AsyncMock,
        mock_api_key_repo: AsyncMock,
        mock_context: MagicMock,
    ) -> None:
        """ValidateKey should return valid=False for revoked keys."""
        revoked_key = ApiKey(
            id=uuid4(),
            account_id=uuid4(),
            key_hash=KeyHash(value="argon2id_hash_value"),
            sha256_key_hash=SHA256KeyHash(value="a" * 64),
            status=KeyStatus.revoked,
            created_at=datetime.now(UTC),
            revoked_at=datetime.now(UTC),
        )
        mock_key_cache.get.return_value = None
        mock_api_key_repo.get_by_sha256_hash.return_value = revoked_key

        request = KeyRequest(key_hash="a" * 64)
        response = await servicer.ValidateKey(request, mock_context)

        assert response.is_valid is False
        assert response.account_id == ""

    @pytest.mark.asyncio
    async def test_validate_key_db_unavailable(
        self,
        servicer: KeyValidationServicer,
        mock_key_cache: AsyncMock,
        mock_api_key_repo: AsyncMock,
        mock_context: MagicMock,
    ) -> None:
        """ValidateKey should abort with UNAVAILABLE when DB is unavailable."""
        mock_key_cache.get.return_value = None
        mock_api_key_repo.get_by_sha256_hash.side_effect = SQLAlchemyError()

        request = KeyRequest(key_hash="a" * 64)
        await servicer.ValidateKey(request, mock_context)

        mock_context.abort.assert_called_once_with(
            StatusCode.UNAVAILABLE, "database unavailable"
        )


class TestBankDirectoryServicer:
    """Tests for BankDirectoryServicer."""

    @pytest.fixture
    def mock_endpoint_cache(self) -> AsyncMock:
        """Create a mock EndpointCache."""
        return AsyncMock()

    @pytest.fixture
    def mock_bank_endpoint_repo(self) -> AsyncMock:
        """Create a mock BankEndpointRepository."""
        return AsyncMock()

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        """Create a mock gRPC context."""
        context = MagicMock()
        context.abort = AsyncMock()
        return context

    @pytest.fixture
    def servicer(
        self, mock_endpoint_cache: AsyncMock, mock_bank_endpoint_repo: AsyncMock
    ) -> BankDirectoryServicer:
        """Create a BankDirectoryServicer with mock dependencies."""
        return BankDirectoryServicer(
            endpoint_cache=mock_endpoint_cache,
            bank_endpoint_repo=mock_bank_endpoint_repo,
        )

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
    async def test_get_bank_endpoint_cache_hit(
        self,
        servicer: BankDirectoryServicer,
        mock_endpoint_cache: AsyncMock,
        mock_context: MagicMock,
        bank_endpoint: BankEndpoint,
    ) -> None:
        """GetBankEndpoint should return endpoint from cache."""
        mock_endpoint_cache.get.return_value = bank_endpoint

        request = GetBankEndpointRequest(bank_code="TEST001")
        response = await servicer.GetBankEndpoint(request, mock_context)

        assert response.bank_code == "TEST001"
        assert response.protocol == "fints"
        assert response.server_url == "https://fints.example.com"
        assert response.fints_product_id == "test_product_id"
        assert response.fints_product_version == "1.0.0"
        assert response.fints_country_code == "DE"

    @pytest.mark.asyncio
    async def test_get_bank_endpoint_cache_miss_db_hit(
        self,
        servicer: BankDirectoryServicer,
        mock_endpoint_cache: AsyncMock,
        mock_bank_endpoint_repo: AsyncMock,
        mock_context: MagicMock,
        bank_endpoint: BankEndpoint,
    ) -> None:
        """GetBankEndpoint should fall back to DB and populate cache."""
        mock_endpoint_cache.get.return_value = None
        mock_bank_endpoint_repo.get.return_value = bank_endpoint

        request = GetBankEndpointRequest(bank_code="TEST001")
        response = await servicer.GetBankEndpoint(request, mock_context)

        assert response.bank_code == "TEST001"
        mock_endpoint_cache.set.assert_called_once_with(bank_endpoint)

    @pytest.mark.asyncio
    async def test_get_bank_endpoint_not_found(
        self,
        servicer: BankDirectoryServicer,
        mock_endpoint_cache: AsyncMock,
        mock_bank_endpoint_repo: AsyncMock,
        mock_context: MagicMock,
    ) -> None:
        """GetBankEndpoint should abort with NOT_FOUND when endpoint not found."""
        mock_endpoint_cache.get.return_value = None
        mock_bank_endpoint_repo.get.return_value = None

        request = GetBankEndpointRequest(bank_code="NONEXISTENT")
        await servicer.GetBankEndpoint(request, mock_context)

        mock_context.abort.assert_called_once_with(
            StatusCode.NOT_FOUND, "bank_code NONEXISTENT not found"
        )

    @pytest.mark.asyncio
    async def test_get_bank_endpoint_db_unavailable(
        self,
        servicer: BankDirectoryServicer,
        mock_endpoint_cache: AsyncMock,
        mock_bank_endpoint_repo: AsyncMock,
        mock_context: MagicMock,
    ) -> None:
        """GetBankEndpoint should abort with UNAVAILABLE when DB is unavailable."""
        mock_endpoint_cache.get.return_value = None
        mock_bank_endpoint_repo.get.side_effect = SQLAlchemyError()

        request = GetBankEndpointRequest(bank_code="TEST001")
        await servicer.GetBankEndpoint(request, mock_context)

        mock_context.abort.assert_called_once_with(
            StatusCode.UNAVAILABLE, "database unavailable"
        )

    @pytest.mark.asyncio
    async def test_get_bank_endpoint_includes_metadata(
        self,
        servicer: BankDirectoryServicer,
        mock_endpoint_cache: AsyncMock,
        mock_context: MagicMock,
        bank_endpoint: BankEndpoint,
    ) -> None:
        """GetBankEndpoint should include metadata in response."""
        mock_endpoint_cache.get.return_value = bank_endpoint

        request = GetBankEndpointRequest(bank_code="TEST001")
        response = await servicer.GetBankEndpoint(request, mock_context)

        assert response.metadata == {"key": "value"}

    @pytest.mark.asyncio
    async def test_get_bank_endpoint_empty_metadata(
        self,
        servicer: BankDirectoryServicer,
        mock_endpoint_cache: AsyncMock,
        mock_context: MagicMock,
    ) -> None:
        """GetBankEndpoint should handle None metadata."""
        endpoint = BankEndpoint(
            bank_code="TEST001",
            protocol=BankingProtocol.fints,
            server_url="https://fints.example.com",
            protocol_config=FinTSConfig(
                product_id=SecretStr("test_product_id"),
                product_version="1.0.0",
                country_code="DE",
            ),
            metadata=None,
        )
        mock_endpoint_cache.get.return_value = endpoint

        request = GetBankEndpointRequest(bank_code="TEST001")
        response = await servicer.GetBankEndpoint(request, mock_context)

        assert response.metadata == {}
