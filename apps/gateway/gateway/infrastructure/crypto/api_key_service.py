"""Argon2id-backed API key generation and verification."""

from __future__ import annotations

import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from gateway.domain.consumer_access import ApiKeyHash, ApiKeyVerifier


class Argon2ApiKeyService(ApiKeyVerifier):
    """Generate, hash, and verify API keys using Argon2id."""

    def __init__(
        self,
        *,
        entropy_bytes: int = 32,
        time_cost: int = 2,
        memory_cost: int = 65_536,
        parallelism: int = 2,
    ) -> None:
        self._entropy_bytes = entropy_bytes
        self._hasher = PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
        )

    def generate(self) -> str:
        return secrets.token_urlsafe(self._entropy_bytes)

    def hash(self, raw_key: str) -> ApiKeyHash:
        return ApiKeyHash(self._hasher.hash(raw_key))

    def verify(self, raw_key: str, stored_hash: ApiKeyHash) -> bool:
        try:
            return bool(self._hasher.verify(stored_hash.value, raw_key))
        except (InvalidHashError, VerificationError, VerifyMismatchError):
            return False
