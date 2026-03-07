"""Unit tests for the RevokeApiKey use case."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from admin.application.api_keys.use_cases import RevokeApiKey
from admin.domain.api_keys.entities.api_key import ApiKey
from admin.domain.api_keys.value_objects.key_hash import KeyHash
from admin.domain.api_keys.value_objects.key_status import KeyStatus
from admin.domain.api_keys.value_objects.sha256_key_hash import SHA256KeyHash
from admin.domain.exceptions import ApiKeyAlreadyRevokedError, ApiKeyNotFoundError


class TestRevokeApiKey:
    """Tests for RevokeApiKey use case."""

    @pytest.fixture
    def mock_api_key_repo(self) -> AsyncMock:
        """Create a mock ApiKeyRepository."""
        return AsyncMock()

    @pytest.fixture
    def mock_key_cache(self) -> AsyncMock:
        """Create a mock KeyCache."""
        return AsyncMock()

    @pytest.fixture
    def use_case(
        self,
        mock_api_key_repo: AsyncMock,
        mock_key_cache: AsyncMock,
    ) -> RevokeApiKey:
        """Create a RevokeApiKey use case with mock dependencies."""
        return RevokeApiKey(
            api_key_repo=mock_api_key_repo,
            key_cache=mock_key_cache,
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

    @pytest.fixture
    def revoked_api_key(self) -> ApiKey:
        """Create a revoked API key for testing."""
        return ApiKey(
            id=uuid4(),
            account_id=uuid4(),
            key_hash=KeyHash(value="argon2id_hash_value"),
            sha256_key_hash=SHA256KeyHash(value="b" * 64),
            status=KeyStatus.revoked,
            created_at=datetime.now(UTC),
            revoked_at=datetime.now(UTC),
        )

    @pytest.mark.asyncio
    async def test_happy_path_revokes_key(
        self,
        use_case: RevokeApiKey,
        mock_api_key_repo: AsyncMock,
        mock_key_cache: AsyncMock,
        active_api_key: ApiKey,
    ) -> None:
        """RevokeApiKey should revoke an active API key."""
        mock_api_key_repo.get.return_value = active_api_key

        await use_case.execute(active_api_key.id)

        mock_api_key_repo.update.assert_called_once()
        updated_key = mock_api_key_repo.update.call_args[0][0]
        assert updated_key.status == KeyStatus.revoked
        assert updated_key.revoked_at is not None

    @pytest.mark.asyncio
    async def test_happy_path_removes_from_cache(
        self,
        use_case: RevokeApiKey,
        mock_api_key_repo: AsyncMock,
        mock_key_cache: AsyncMock,
        active_api_key: ApiKey,
    ) -> None:
        """RevokeApiKey should remove the key from cache."""
        mock_api_key_repo.get.return_value = active_api_key

        await use_case.execute(active_api_key.id)

        mock_key_cache.delete.assert_called_once_with(active_api_key.sha256_key_hash)

    @pytest.mark.asyncio
    async def test_cache_removal_happens_before_db_update(
        self,
        use_case: RevokeApiKey,
        mock_api_key_repo: AsyncMock,
        mock_key_cache: AsyncMock,
        active_api_key: ApiKey,
    ) -> None:
        """RevokeApiKey should remove from cache BEFORE updating the database.

        This is critical for security: ensures no window where a revoked key
        is still valid in the cache.
        """
        mock_api_key_repo.get.return_value = active_api_key

        # Track call order
        call_order = []
        mock_key_cache.delete.side_effect = lambda x: call_order.append("cache_delete")
        mock_api_key_repo.update.side_effect = lambda x: call_order.append("db_update")

        await use_case.execute(active_api_key.id)

        assert call_order == ["cache_delete", "db_update"]

    @pytest.mark.asyncio
    async def test_key_not_found_raises_error(
        self,
        use_case: RevokeApiKey,
        mock_api_key_repo: AsyncMock,
    ) -> None:
        """RevokeApiKey should raise ApiKeyNotFoundError if key doesn't exist."""
        mock_api_key_repo.get.return_value = None
        key_id = uuid4()

        with pytest.raises(ApiKeyNotFoundError) as exc_info:
            await use_case.execute(key_id)

        assert str(key_id) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_already_revoked_raises_error(
        self,
        use_case: RevokeApiKey,
        mock_api_key_repo: AsyncMock,
        revoked_api_key: ApiKey,
    ) -> None:
        """RevokeApiKey should raise ApiKeyAlreadyRevokedError if key is already revoked."""
        mock_api_key_repo.get.return_value = revoked_api_key

        with pytest.raises(ApiKeyAlreadyRevokedError) as exc_info:
            await use_case.execute(revoked_api_key.id)

        assert str(revoked_api_key.id) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_preserves_original_key_data(
        self,
        use_case: RevokeApiKey,
        mock_api_key_repo: AsyncMock,
        mock_key_cache: AsyncMock,
        active_api_key: ApiKey,
    ) -> None:
        """RevokeApiKey should preserve original key data when revoking."""
        mock_api_key_repo.get.return_value = active_api_key

        await use_case.execute(active_api_key.id)

        updated_key = mock_api_key_repo.update.call_args[0][0]
        assert updated_key.id == active_api_key.id
        assert updated_key.account_id == active_api_key.account_id
        assert updated_key.key_hash == active_api_key.key_hash
        assert updated_key.sha256_key_hash == active_api_key.sha256_key_hash
        assert updated_key.created_at == active_api_key.created_at
