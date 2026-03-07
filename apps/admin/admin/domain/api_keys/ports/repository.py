"""Repository ports for the api_keys bounded context."""

from typing import Protocol
from uuid import UUID

from admin.domain.api_keys.entities.account import Account
from admin.domain.api_keys.entities.api_key import ApiKey
from admin.domain.api_keys.value_objects.sha256_key_hash import SHA256KeyHash


class AccountRepository(Protocol):
    """Port for persisting and retrieving Account aggregates."""

    async def get(self, account_id: UUID) -> Account | None:
        """Retrieve an account by ID."""
        ...

    async def save(self, account: Account) -> None:
        """Persist a new account."""
        ...

    async def delete(self, account_id: UUID) -> None:
        """Delete an account by ID."""
        ...

    async def has_api_keys(self, account_id: UUID) -> bool:
        """Check if an account has any associated API keys."""
        ...


class ApiKeyRepository(Protocol):
    """Port for persisting and retrieving ApiKey entities."""

    async def get(self, key_id: UUID) -> ApiKey | None:
        """Retrieve an API key by ID."""
        ...

    async def get_active_for_account(self, account_id: UUID) -> ApiKey | None:
        """Retrieve the active API key for an account, if any."""
        ...

    async def get_by_sha256_hash(self, sha256_hash: SHA256KeyHash) -> ApiKey | None:
        """Retrieve an API key by its SHA-256 hash."""
        ...

    async def list_active(self) -> list[ApiKey]:
        """List all active API keys."""
        ...

    async def list_for_account(self, account_id: UUID) -> list[ApiKey]:
        """List all API keys for an account."""
        ...

    async def save(self, api_key: ApiKey) -> None:
        """Persist a new API key."""
        ...

    async def update(self, api_key: ApiKey) -> None:
        """Update an existing API key."""
        ...
