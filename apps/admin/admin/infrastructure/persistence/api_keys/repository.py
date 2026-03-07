"""Repository implementations for the api_keys bounded context."""

from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from admin.domain.api_keys.entities.account import Account
from admin.domain.api_keys.entities.api_key import ApiKey
from admin.domain.api_keys.value_objects.key_hash import KeyHash
from admin.domain.api_keys.value_objects.key_status import KeyStatus
from admin.domain.api_keys.value_objects.sha256_key_hash import SHA256KeyHash
from admin.infrastructure.persistence.api_keys.models import AccountORM, ApiKeyORM


class AccountRepositoryImpl:
    """Implementation of AccountRepository using SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, account_id: UUID) -> Account | None:
        """Retrieve an account by ID."""
        result = await self._session.execute(
            select(AccountORM).where(AccountORM.id == account_id)
        )
        orm_account = result.scalar_one_or_none()
        if orm_account is None:
            return None
        return self._to_domain(orm_account)

    async def save(self, account: Account) -> None:
        """Persist a new account."""
        orm_account = AccountORM(
            id=account.id,
            created_at=account.created_at,
        )
        self._session.add(orm_account)
        await self._session.flush()

    async def delete(self, account_id: UUID) -> None:
        """Delete an account by ID."""
        result = await self._session.execute(
            select(AccountORM).where(AccountORM.id == account_id)
        )
        orm_account = result.scalar_one_or_none()
        if orm_account is not None:
            await self._session.delete(orm_account)
            await self._session.flush()

    async def has_api_keys(self, account_id: UUID) -> bool:
        """Check if an account has any associated API keys."""
        result = await self._session.execute(
            select(exists().where(ApiKeyORM.account_id == account_id))
        )
        return result.scalar() or False

    @staticmethod
    def _to_domain(orm_account: AccountORM) -> Account:
        """Convert ORM model to domain entity."""
        return Account(
            id=orm_account.id,
            created_at=orm_account.created_at,
        )


class ApiKeyRepositoryImpl:
    """Implementation of ApiKeyRepository using SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, key_id: UUID) -> ApiKey | None:
        """Retrieve an API key by ID."""
        result = await self._session.execute(
            select(ApiKeyORM).where(ApiKeyORM.id == key_id)
        )
        orm_key = result.scalar_one_or_none()
        if orm_key is None:
            return None
        return self._to_domain(orm_key)

    async def get_active_for_account(self, account_id: UUID) -> ApiKey | None:
        """Retrieve the active API key for an account, if any."""
        result = await self._session.execute(
            select(ApiKeyORM).where(
                ApiKeyORM.account_id == account_id,
                ApiKeyORM.status == KeyStatus.active.value,
            )
        )
        orm_key = result.scalar_one_or_none()
        if orm_key is None:
            return None
        return self._to_domain(orm_key)

    async def get_by_sha256_hash(self, sha256_hash: SHA256KeyHash) -> ApiKey | None:
        """Retrieve an API key by its SHA-256 hash."""
        result = await self._session.execute(
            select(ApiKeyORM).where(ApiKeyORM.sha256_key_hash == sha256_hash.value)
        )
        orm_key = result.scalar_one_or_none()
        if orm_key is None:
            return None
        return self._to_domain(orm_key)

    async def list_active(self) -> list[ApiKey]:
        """List all active API keys."""
        result = await self._session.execute(
            select(ApiKeyORM).where(ApiKeyORM.status == KeyStatus.active.value)
        )
        return [self._to_domain(orm_key) for orm_key in result.scalars().all()]

    async def list_for_account(self, account_id: UUID) -> list[ApiKey]:
        """List all API keys for an account."""
        result = await self._session.execute(
            select(ApiKeyORM).where(ApiKeyORM.account_id == account_id)
        )
        return [self._to_domain(orm_key) for orm_key in result.scalars().all()]

    async def save(self, api_key: ApiKey) -> None:
        """Persist a new API key."""
        orm_key = ApiKeyORM(
            id=api_key.id,
            account_id=api_key.account_id,
            key_hash=api_key.key_hash.value,
            sha256_key_hash=api_key.sha256_key_hash.value,
            status=api_key.status.value,
            created_at=api_key.created_at,
            revoked_at=api_key.revoked_at,
        )
        self._session.add(orm_key)
        await self._session.flush()

    async def update(self, api_key: ApiKey) -> None:
        """Update an existing API key."""
        result = await self._session.execute(
            select(ApiKeyORM).where(ApiKeyORM.id == api_key.id)
        )
        orm_key = result.scalar_one_or_none()
        if orm_key is not None:
            orm_key.status = api_key.status.value
            orm_key.revoked_at = api_key.revoked_at
            await self._session.flush()

    @staticmethod
    def _to_domain(orm_key: ApiKeyORM) -> ApiKey:
        """Convert ORM model to domain entity."""
        return ApiKey(
            id=orm_key.id,
            account_id=orm_key.account_id,
            key_hash=KeyHash(value=orm_key.key_hash),
            sha256_key_hash=SHA256KeyHash(value=orm_key.sha256_key_hash),
            status=KeyStatus(orm_key.status),
            created_at=orm_key.created_at,
            revoked_at=orm_key.revoked_at,
        )
