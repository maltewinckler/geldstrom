"""Use cases for the api_keys bounded context."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from admin.domain.api_keys.entities.account import Account
from admin.domain.api_keys.entities.api_key import ApiKey
from admin.domain.api_keys.ports.repository import AccountRepository, ApiKeyRepository
from admin.domain.api_keys.ports.services import KeyCache, KeyHasher
from admin.domain.api_keys.value_objects.key_status import KeyStatus
from admin.domain.api_keys.value_objects.raw_key import RawKey
from admin.domain.api_keys.value_objects.sha256_key_hash import SHA256KeyHash
from admin.domain.exceptions import (
    AccountHasKeysError,
    AccountNotFoundError,
    ApiKeyAlreadyExistsError,
    ApiKeyAlreadyRevokedError,
    ApiKeyNotFoundError,
)


class CreateAccount:
    """Use case for creating a new account."""

    def __init__(self, account_repo: AccountRepository) -> None:
        self._account_repo = account_repo

    async def execute(self, account_id: UUID) -> Account:
        """Create a new account.

        Raises:
            AccountAlreadyExistsError: If an account with the given ID already exists
                (mapped from IntegrityError in repository).
        """
        account = Account(
            id=account_id,
            created_at=datetime.now(UTC),
        )
        await self._account_repo.save(account)
        return account


class GetAccount:
    """Use case for retrieving an account with its API keys."""

    def __init__(
        self,
        account_repo: AccountRepository,
        api_key_repo: ApiKeyRepository,
    ) -> None:
        self._account_repo = account_repo
        self._api_key_repo = api_key_repo

    async def execute(self, account_id: UUID) -> tuple[Account, list[ApiKey]]:
        """Retrieve an account and its associated API keys.

        Raises:
            AccountNotFoundError: If the account does not exist.
        """
        account = await self._account_repo.get(account_id)
        if account is None:
            raise AccountNotFoundError(f"Account {account_id} not found")

        api_keys = await self._api_key_repo.list_for_account(account_id)
        return account, api_keys


class DeleteAccount:
    """Use case for deleting an account."""

    def __init__(self, account_repo: AccountRepository) -> None:
        self._account_repo = account_repo

    async def execute(self, account_id: UUID) -> None:
        """Delete an account.

        Raises:
            AccountNotFoundError: If the account does not exist.
            AccountHasKeysError: If the account has any associated API keys.
        """
        account = await self._account_repo.get(account_id)
        if account is None:
            raise AccountNotFoundError(f"Account {account_id} not found")

        has_keys = await self._account_repo.has_api_keys(account_id)
        if has_keys:
            raise AccountHasKeysError(
                f"Account {account_id} has API keys. Revoke and delete keys first."
            )

        await self._account_repo.delete(account_id)


class CreateApiKey:
    """Use case for creating a new API key for an account."""

    def __init__(
        self,
        account_repo: AccountRepository,
        api_key_repo: ApiKeyRepository,
        key_hasher: KeyHasher,
        key_cache: KeyCache,
    ) -> None:
        self._account_repo = account_repo
        self._api_key_repo = api_key_repo
        self._key_hasher = key_hasher
        self._key_cache = key_cache

    async def execute(self, account_id: UUID) -> tuple[UUID, RawKey]:
        """Create a new API key for an account.

        Returns:
            A tuple of (key_id, raw_key). The raw_key is returned exactly once.

        Raises:
            AccountNotFoundError: If the account does not exist.
            ApiKeyAlreadyExistsError: If an active API key already exists for the account.
        """
        # 1. Verify account exists
        account = await self._account_repo.get(account_id)
        if account is None:
            raise AccountNotFoundError(f"Account {account_id} not found")

        # 2. Check no active key exists for account
        existing_key = await self._api_key_repo.get_active_for_account(account_id)
        if existing_key is not None:
            raise ApiKeyAlreadyExistsError(
                f"Active API key already exists for account {account_id}"
            )

        # 3. Generate RawKey
        raw_key = RawKey.generate()

        # 4. Compute KeyHash via KeyHasher (Argon2id)
        key_hash = await self._key_hasher.hash(raw_key)

        # 5. Compute SHA256KeyHash
        sha256_key_hash = SHA256KeyHash.from_raw_key(raw_key)

        # 6. Persist ApiKey to PostgreSQL
        key_id = uuid4()
        api_key = ApiKey(
            id=key_id,
            account_id=account_id,
            key_hash=key_hash,
            sha256_key_hash=sha256_key_hash,
            status=KeyStatus.active,
            created_at=datetime.now(UTC),
        )
        await self._api_key_repo.save(api_key)

        # 7. Update internal cache
        await self._key_cache.set(sha256_key_hash, account_id)

        # 8. Return key_id and RawKey
        return key_id, raw_key


class RevokeApiKey:
    """Use case for revoking an API key."""

    def __init__(
        self,
        api_key_repo: ApiKeyRepository,
        key_cache: KeyCache,
    ) -> None:
        self._api_key_repo = api_key_repo
        self._key_cache = key_cache

    async def execute(self, key_id: UUID) -> None:
        """Revoke an API key.

        IMPORTANT: Cache is removed BEFORE database update to ensure no window
        where a revoked key is still valid in the cache.

        Raises:
            ApiKeyNotFoundError: If the API key does not exist.
            ApiKeyAlreadyRevokedError: If the API key is already revoked.
        """
        # 1. Load ApiKey
        api_key = await self._api_key_repo.get(key_id)
        if api_key is None:
            raise ApiKeyNotFoundError(f"API key {key_id} not found")

        # 2. Assert status == active
        if api_key.status == KeyStatus.revoked:
            raise ApiKeyAlreadyRevokedError(f"API key {key_id} is already revoked")

        # 3. Remove from cache FIRST (before DB update)
        await self._key_cache.delete(api_key.sha256_key_hash)

        # 4. Set status = revoked, revoked_at = now()
        revoked_key = ApiKey(
            id=api_key.id,
            account_id=api_key.account_id,
            key_hash=api_key.key_hash,
            sha256_key_hash=api_key.sha256_key_hash,
            status=KeyStatus.revoked,
            created_at=api_key.created_at,
            revoked_at=datetime.now(UTC),
        )

        # 5. Persist to PostgreSQL
        await self._api_key_repo.update(revoked_key)


class RotateApiKey:
    """Use case for rotating an API key."""

    def __init__(
        self,
        api_key_repo: ApiKeyRepository,
        key_hasher: KeyHasher,
        key_cache: KeyCache,
    ) -> None:
        self._api_key_repo = api_key_repo
        self._key_hasher = key_hasher
        self._key_cache = key_cache

    async def execute(self, key_id: UUID) -> tuple[UUID, RawKey]:
        """Rotate an API key, revoking the old one and creating a new one.

        IMPORTANT: Old key is removed from cache BEFORE database operations
        to ensure no window where a revoked key is still valid in the cache.

        Returns:
            A tuple of (new_key_id, new_raw_key). The raw_key is returned exactly once.

        Raises:
            ApiKeyNotFoundError: If the API key does not exist.
            ApiKeyAlreadyRevokedError: If the API key is already revoked.
        """
        # 1. Load existing ApiKey (must be active)
        old_key = await self._api_key_repo.get(key_id)
        if old_key is None:
            raise ApiKeyNotFoundError(f"API key {key_id} not found")

        if old_key.status == KeyStatus.revoked:
            raise ApiKeyAlreadyRevokedError(f"API key {key_id} is already revoked")

        # 2. Remove old key from cache FIRST
        await self._key_cache.delete(old_key.sha256_key_hash)

        # 3. Within single DB transaction:
        #    a. Revoke old key
        revoked_old_key = ApiKey(
            id=old_key.id,
            account_id=old_key.account_id,
            key_hash=old_key.key_hash,
            sha256_key_hash=old_key.sha256_key_hash,
            status=KeyStatus.revoked,
            created_at=old_key.created_at,
            revoked_at=datetime.now(UTC),
        )

        #    b. Generate new RawKey, KeyHash, SHA256KeyHash
        new_raw_key = RawKey.generate()
        new_key_hash = await self._key_hasher.hash(new_raw_key)
        new_sha256_key_hash = SHA256KeyHash.from_raw_key(new_raw_key)

        #    c. Persist new ApiKey
        new_key_id = uuid4()
        new_api_key = ApiKey(
            id=new_key_id,
            account_id=old_key.account_id,
            key_hash=new_key_hash,
            sha256_key_hash=new_sha256_key_hash,
            status=KeyStatus.active,
            created_at=datetime.now(UTC),
        )

        # Note: In a real implementation, these two operations should be
        # wrapped in a database transaction. The repository implementation
        # should handle transaction management.
        await self._api_key_repo.update(revoked_old_key)
        await self._api_key_repo.save(new_api_key)

        # 4. Add new key to cache
        await self._key_cache.set(new_sha256_key_hash, old_key.account_id)

        # 5. Return new key_id and RawKey
        return new_key_id, new_raw_key
