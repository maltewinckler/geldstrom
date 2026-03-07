"""Argon2id key hasher implementation."""

import asyncio

from argon2 import PasswordHasher, Type

from admin.domain.api_keys.value_objects.key_hash import KeyHash
from admin.domain.api_keys.value_objects.raw_key import RawKey


class Argon2idKeyHasher:
    """Argon2id hasher for API keys.

    Parameters: time_cost=3, memory_cost=65536, parallelism=4, hash_len=32.
    """

    def __init__(self) -> None:
        """Initialize the hasher with secure parameters."""
        self._hasher = PasswordHasher(
            time_cost=3,
            memory_cost=65536,
            parallelism=4,
            hash_len=32,
            type=Type.ID,
        )

    async def hash(self, raw_key: RawKey) -> KeyHash:
        """Compute the Argon2id hash of a raw key.

        Runs in executor to avoid blocking the event loop.
        """
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, self._hasher.hash, raw_key.value.get_secret_value()
        )
        return KeyHash(value=result)

    async def verify(self, raw_key: RawKey, key_hash: KeyHash) -> bool:
        """Verify a raw key against an Argon2id hash.

        Runs in executor to avoid blocking the event loop.
        """
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                None,
                self._hasher.verify,
                key_hash.value,
                raw_key.value.get_secret_value(),
            )
            return True
        except Exception:
            return False
