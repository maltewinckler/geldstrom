"""Service ports for the api_keys bounded context."""

from typing import Protocol
from uuid import UUID

from admin.domain.api_keys.value_objects.key_hash import KeyHash
from admin.domain.api_keys.value_objects.raw_key import RawKey
from admin.domain.api_keys.value_objects.sha256_key_hash import SHA256KeyHash


class KeyHasher(Protocol):
    """Port for computing Argon2id hashes of raw keys."""

    async def hash(self, raw_key: RawKey) -> KeyHash:
        """Compute the Argon2id hash of a raw key."""
        ...

    async def verify(self, raw_key: RawKey, key_hash: KeyHash) -> bool:
        """Verify a raw key against an Argon2id hash."""
        ...


class KeyCache(Protocol):
    """Internal cache for fast key validation.

    Implementation detail.
    """

    async def get(self, sha256_hash: SHA256KeyHash) -> str | None:
        """Get the account_id for a SHA-256 hash, or None if not cached."""
        ...

    async def set(self, sha256_hash: SHA256KeyHash, account_id: UUID) -> None:
        """Cache a SHA-256 hash to account_id mapping."""
        ...

    async def delete(self, sha256_hash: SHA256KeyHash) -> None:
        """Remove a SHA-256 hash from the cache."""
        ...

    async def load_all(self, keys: list[tuple[SHA256KeyHash, UUID]]) -> None:
        """Load multiple SHA-256 hash to account_id mappings into the cache."""
        ...
