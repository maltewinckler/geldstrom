"""In-memory key cache implementation."""

from uuid import UUID

from admin.domain.api_keys.value_objects.sha256_key_hash import SHA256KeyHash


class InMemoryKeyCache:
    """Simple dict-based cache for API key validation.

    Maps SHA-256 hashes to account IDs for fast gRPC lookups.
    """

    def __init__(self) -> None:
        """Initialize an empty cache."""
        self._cache: dict[str, str] = {}  # sha256_hash -> account_id

    async def get(self, sha256_hash: SHA256KeyHash) -> str | None:
        """Get the account_id for a SHA-256 hash, or None if not cached."""
        return self._cache.get(sha256_hash.value)

    async def set(self, sha256_hash: SHA256KeyHash, account_id: UUID) -> None:
        """Cache a SHA-256 hash to account_id mapping."""
        self._cache[sha256_hash.value] = str(account_id)

    async def delete(self, sha256_hash: SHA256KeyHash) -> None:
        """Remove a SHA-256 hash from the cache."""
        self._cache.pop(sha256_hash.value, None)

    async def load_all(self, keys: list[tuple[SHA256KeyHash, UUID]]) -> None:
        """Load multiple SHA-256 hash to account_id mappings into the cache."""
        for sha256_hash, account_id in keys:
            self._cache[sha256_hash.value] = str(account_id)
