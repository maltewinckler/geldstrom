"""Unit tests for the RotateApiKey use case."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from admin.application.api_keys.use_cases import RotateApiKey
from admin.domain.api_keys.entities.api_key import ApiKey
from admin.domain.api_keys.value_objects.key_hash import KeyHash
from admin.domain.api_keys.value_objects.key_status import KeyStatus
from admin.domain.api_keys.value_objects.raw_key import RawKey
from admin.domain.api_keys.value_objects.sha256_key_hash import SHA256KeyHash
from admin.domain.exceptions import ApiKeyAlreadyRevokedError, ApiKeyNotFoundError


class TestRotateApiKey:
    """Tests for RotateApiKey use case."""

    @pytest.fixture
    def mock_api_key_repo(self) -> AsyncMock:
        """Create a mock ApiKeyRepository."""
        return AsyncMock()

    @pytest.fixture
    def mock_key_hasher(self) -> AsyncMock:
        """Create a mock KeyHasher."""
        hasher = AsyncMock()
        hasher.hash.return_value = KeyHash(value="new_argon2id_hash_value")
        return hasher

    @pytest.fixture
    def mock_key_cache(self) -> AsyncMock:
        """Create a mock KeyCache."""
        return AsyncMock()

    @pytest.fixture
    def use_case(
        self,
        mock_api_key_repo: AsyncMock,
        mock_key_hasher: AsyncMock,
        mock_key_cache: AsyncMock,
    ) -> RotateApiKey:
        """Create a RotateApiKey use case with mock dependencies."""
        return RotateApiKey(
            api_key_repo=mock_api_key_repo,
            key_hasher=mock_key_hasher,
            key_cache=mock_key_cache,
        )

    @pytest.fixture
    def active_api_key(self) -> ApiKey:
        """Create an active API key for testing."""
        return ApiKey(
            id=uuid4(),
            account_id=uuid4(),
            key_hash=KeyHash(value="old_argon2id_hash_value"),
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
    async def test_happy_path_returns_new_key(
        self,
        use_case: RotateApiKey,
        mock_api_key_repo: AsyncMock,
        mock_key_hasher: AsyncMock,
        mock_key_cache: AsyncMock,
        active_api_key: ApiKey,
    ) -> None:
        """RotateApiKey should return a new key ID and raw key."""
        mock_api_key_repo.get.return_value = active_api_key

        new_key_id, new_raw_key = await use_case.execute(active_api_key.id)

        assert isinstance(new_raw_key, RawKey)
        assert len(new_raw_key.value.get_secret_value()) == 64
        assert new_key_id != active_api_key.id

    @pytest.mark.asyncio
    async def test_happy_path_revokes_old_key(
        self,
        use_case: RotateApiKey,
        mock_api_key_repo: AsyncMock,
        mock_key_hasher: AsyncMock,
        mock_key_cache: AsyncMock,
        active_api_key: ApiKey,
    ) -> None:
        """RotateApiKey should revoke the old key."""
        mock_api_key_repo.get.return_value = active_api_key

        await use_case.execute(active_api_key.id)

        # First call to update should be the revoked old key
        update_call = mock_api_key_repo.update.call_args[0][0]
        assert update_call.id == active_api_key.id
        assert update_call.status == KeyStatus.revoked
        assert update_call.revoked_at is not None

    @pytest.mark.asyncio
    async def test_happy_path_creates_new_key(
        self,
        use_case: RotateApiKey,
        mock_api_key_repo: AsyncMock,
        mock_key_hasher: AsyncMock,
        mock_key_cache: AsyncMock,
        active_api_key: ApiKey,
    ) -> None:
        """RotateApiKey should create a new key for the same account."""
        mock_api_key_repo.get.return_value = active_api_key

        await use_case.execute(active_api_key.id)

        # save should be called with the new key
        mock_api_key_repo.save.assert_called_once()
        new_key = mock_api_key_repo.save.call_args[0][0]
        assert new_key.account_id == active_api_key.account_id
        assert new_key.status == KeyStatus.active
        assert new_key.id != active_api_key.id

    @pytest.mark.asyncio
    async def test_cache_removal_happens_before_db_operations(
        self,
        use_case: RotateApiKey,
        mock_api_key_repo: AsyncMock,
        mock_key_hasher: AsyncMock,
        mock_key_cache: AsyncMock,
        active_api_key: ApiKey,
    ) -> None:
        """RotateApiKey should remove old key from cache BEFORE database operations.

        This is critical for security: ensures no window where a revoked key
        is still valid in the cache.
        """
        mock_api_key_repo.get.return_value = active_api_key

        # Track call order
        call_order = []
        mock_key_cache.delete.side_effect = lambda x: call_order.append("cache_delete")
        mock_api_key_repo.update.side_effect = lambda x: call_order.append("db_update")
        mock_api_key_repo.save.side_effect = lambda x: call_order.append("db_save")
        mock_key_cache.set.side_effect = lambda x, y: call_order.append("cache_set")

        await use_case.execute(active_api_key.id)

        # Cache delete must happen before any DB operations
        assert call_order.index("cache_delete") < call_order.index("db_update")
        assert call_order.index("cache_delete") < call_order.index("db_save")
        # Cache set happens after DB operations
        assert call_order.index("cache_set") > call_order.index("db_save")

    @pytest.mark.asyncio
    async def test_atomicity_both_operations_happen(
        self,
        use_case: RotateApiKey,
        mock_api_key_repo: AsyncMock,
        mock_key_hasher: AsyncMock,
        mock_key_cache: AsyncMock,
        active_api_key: ApiKey,
    ) -> None:
        """RotateApiKey should perform both revoke and create operations."""
        mock_api_key_repo.get.return_value = active_api_key

        await use_case.execute(active_api_key.id)

        # Both update (revoke) and save (create) should be called
        mock_api_key_repo.update.assert_called_once()
        mock_api_key_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_new_key_added_to_cache(
        self,
        use_case: RotateApiKey,
        mock_api_key_repo: AsyncMock,
        mock_key_hasher: AsyncMock,
        mock_key_cache: AsyncMock,
        active_api_key: ApiKey,
    ) -> None:
        """RotateApiKey should add the new key to the cache."""
        mock_api_key_repo.get.return_value = active_api_key

        await use_case.execute(active_api_key.id)

        mock_key_cache.set.assert_called_once()
        call_args = mock_key_cache.set.call_args[0]
        assert isinstance(call_args[0], SHA256KeyHash)
        assert call_args[1] == active_api_key.account_id

    @pytest.mark.asyncio
    async def test_key_not_found_raises_error(
        self,
        use_case: RotateApiKey,
        mock_api_key_repo: AsyncMock,
    ) -> None:
        """RotateApiKey should raise ApiKeyNotFoundError if key doesn't exist."""
        mock_api_key_repo.get.return_value = None
        key_id = uuid4()

        with pytest.raises(ApiKeyNotFoundError) as exc_info:
            await use_case.execute(key_id)

        assert str(key_id) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_already_revoked_raises_error(
        self,
        use_case: RotateApiKey,
        mock_api_key_repo: AsyncMock,
        revoked_api_key: ApiKey,
    ) -> None:
        """RotateApiKey should raise ApiKeyAlreadyRevokedError if key is already revoked."""
        mock_api_key_repo.get.return_value = revoked_api_key

        with pytest.raises(ApiKeyAlreadyRevokedError) as exc_info:
            await use_case.execute(revoked_api_key.id)

        assert str(revoked_api_key.id) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_hashes_new_raw_key(
        self,
        use_case: RotateApiKey,
        mock_api_key_repo: AsyncMock,
        mock_key_hasher: AsyncMock,
        mock_key_cache: AsyncMock,
        active_api_key: ApiKey,
    ) -> None:
        """RotateApiKey should hash the new raw key using the KeyHasher."""
        mock_api_key_repo.get.return_value = active_api_key

        await use_case.execute(active_api_key.id)

        mock_key_hasher.hash.assert_called_once()
        hashed_key = mock_key_hasher.hash.call_args[0][0]
        assert isinstance(hashed_key, RawKey)
