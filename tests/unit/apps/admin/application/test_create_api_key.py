"""Unit tests for the CreateApiKey use case."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from admin.application.api_keys.use_cases import CreateApiKey
from admin.domain.api_keys.entities.account import Account
from admin.domain.api_keys.entities.api_key import ApiKey
from admin.domain.api_keys.value_objects.key_hash import KeyHash
from admin.domain.api_keys.value_objects.key_status import KeyStatus
from admin.domain.api_keys.value_objects.raw_key import RawKey
from admin.domain.api_keys.value_objects.sha256_key_hash import SHA256KeyHash
from admin.domain.exceptions import AccountNotFoundError, ApiKeyAlreadyExistsError


class TestCreateApiKey:
    """Tests for CreateApiKey use case."""

    @pytest.fixture
    def mock_account_repo(self) -> AsyncMock:
        """Create a mock AccountRepository."""
        return AsyncMock()

    @pytest.fixture
    def mock_api_key_repo(self) -> AsyncMock:
        """Create a mock ApiKeyRepository."""
        return AsyncMock()

    @pytest.fixture
    def mock_key_hasher(self) -> AsyncMock:
        """Create a mock KeyHasher."""
        hasher = AsyncMock()
        hasher.hash.return_value = KeyHash(value="argon2id_hash_value")
        return hasher

    @pytest.fixture
    def mock_key_cache(self) -> AsyncMock:
        """Create a mock KeyCache."""
        return AsyncMock()

    @pytest.fixture
    def use_case(
        self,
        mock_account_repo: AsyncMock,
        mock_api_key_repo: AsyncMock,
        mock_key_hasher: AsyncMock,
        mock_key_cache: AsyncMock,
    ) -> CreateApiKey:
        """Create a CreateApiKey use case with mock dependencies."""
        return CreateApiKey(
            account_repo=mock_account_repo,
            api_key_repo=mock_api_key_repo,
            key_hasher=mock_key_hasher,
            key_cache=mock_key_cache,
        )

    @pytest.fixture
    def existing_account(self) -> Account:
        """Create an existing account for testing."""
        return Account(
            id=uuid4(),
            created_at=datetime.now(UTC),
        )

    @pytest.mark.asyncio
    async def test_happy_path_creates_api_key(
        self,
        use_case: CreateApiKey,
        mock_account_repo: AsyncMock,
        mock_api_key_repo: AsyncMock,
        mock_key_hasher: AsyncMock,
        mock_key_cache: AsyncMock,
        existing_account: Account,
    ) -> None:
        """CreateApiKey should create an API key for an existing account."""
        mock_account_repo.get.return_value = existing_account
        mock_api_key_repo.get_active_for_account.return_value = None

        key_id, raw_key = await use_case.execute(existing_account.id)

        assert isinstance(raw_key, RawKey)
        assert len(raw_key.value.get_secret_value()) == 64

    @pytest.mark.asyncio
    async def test_happy_path_saves_api_key_to_repository(
        self,
        use_case: CreateApiKey,
        mock_account_repo: AsyncMock,
        mock_api_key_repo: AsyncMock,
        mock_key_hasher: AsyncMock,
        mock_key_cache: AsyncMock,
        existing_account: Account,
    ) -> None:
        """CreateApiKey should save the API key to the repository."""
        mock_account_repo.get.return_value = existing_account
        mock_api_key_repo.get_active_for_account.return_value = None

        await use_case.execute(existing_account.id)

        mock_api_key_repo.save.assert_called_once()
        saved_key = mock_api_key_repo.save.call_args[0][0]
        assert isinstance(saved_key, ApiKey)
        assert saved_key.account_id == existing_account.id
        assert saved_key.status == KeyStatus.active

    @pytest.mark.asyncio
    async def test_happy_path_updates_cache(
        self,
        use_case: CreateApiKey,
        mock_account_repo: AsyncMock,
        mock_api_key_repo: AsyncMock,
        mock_key_hasher: AsyncMock,
        mock_key_cache: AsyncMock,
        existing_account: Account,
    ) -> None:
        """CreateApiKey should update the cache with the new key."""
        mock_account_repo.get.return_value = existing_account
        mock_api_key_repo.get_active_for_account.return_value = None

        await use_case.execute(existing_account.id)

        mock_key_cache.set.assert_called_once()
        call_args = mock_key_cache.set.call_args[0]
        assert isinstance(call_args[0], SHA256KeyHash)
        assert call_args[1] == existing_account.id

    @pytest.mark.asyncio
    async def test_happy_path_hashes_raw_key(
        self,
        use_case: CreateApiKey,
        mock_account_repo: AsyncMock,
        mock_api_key_repo: AsyncMock,
        mock_key_hasher: AsyncMock,
        mock_key_cache: AsyncMock,
        existing_account: Account,
    ) -> None:
        """CreateApiKey should hash the raw key using the KeyHasher."""
        mock_account_repo.get.return_value = existing_account
        mock_api_key_repo.get_active_for_account.return_value = None

        await use_case.execute(existing_account.id)

        mock_key_hasher.hash.assert_called_once()
        hashed_key = mock_key_hasher.hash.call_args[0][0]
        assert isinstance(hashed_key, RawKey)

    @pytest.mark.asyncio
    async def test_account_not_found_raises_error(
        self,
        use_case: CreateApiKey,
        mock_account_repo: AsyncMock,
    ) -> None:
        """CreateApiKey should raise AccountNotFoundError if account doesn't exist."""
        mock_account_repo.get.return_value = None
        account_id = uuid4()

        with pytest.raises(AccountNotFoundError) as exc_info:
            await use_case.execute(account_id)

        assert str(account_id) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_key_already_exists_raises_error(
        self,
        use_case: CreateApiKey,
        mock_account_repo: AsyncMock,
        mock_api_key_repo: AsyncMock,
        existing_account: Account,
    ) -> None:
        """CreateApiKey should raise ApiKeyAlreadyExistsError if active key exists."""
        mock_account_repo.get.return_value = existing_account
        existing_key = ApiKey(
            id=uuid4(),
            account_id=existing_account.id,
            key_hash=KeyHash(value="existing_hash"),
            sha256_key_hash=SHA256KeyHash(value="a" * 64),
            status=KeyStatus.active,
            created_at=datetime.now(UTC),
        )
        mock_api_key_repo.get_active_for_account.return_value = existing_key

        with pytest.raises(ApiKeyAlreadyExistsError) as exc_info:
            await use_case.execute(existing_account.id)

        assert str(existing_account.id) in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_returns_key_id_and_raw_key(
        self,
        use_case: CreateApiKey,
        mock_account_repo: AsyncMock,
        mock_api_key_repo: AsyncMock,
        mock_key_hasher: AsyncMock,
        mock_key_cache: AsyncMock,
        existing_account: Account,
    ) -> None:
        """CreateApiKey should return a tuple of (key_id, raw_key)."""
        mock_account_repo.get.return_value = existing_account
        mock_api_key_repo.get_active_for_account.return_value = None

        result = await use_case.execute(existing_account.id)

        assert isinstance(result, tuple)
        assert len(result) == 2
        key_id, raw_key = result
        assert isinstance(key_id, type(uuid4()))
        assert isinstance(raw_key, RawKey)
