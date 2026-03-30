"""Argon2 API key service for the admin CLI (generate+hash only)."""

from __future__ import annotations

import base64
import secrets

from argon2 import PasswordHasher

from gateway_admin_cli.domain.users import ApiKeyHash

_KEY_BYTES = 32


class Argon2AdminApiKeyService:
    """Generates cryptographically secure API keys and hashes them with Argon2id."""

    def __init__(
        self,
        *,
        time_cost: int = 2,
        memory_cost: int = 65536,
        parallelism: int = 1,
    ) -> None:
        self._hasher = PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
        )

    def generate(self) -> str:
        return (
            base64.urlsafe_b64encode(secrets.token_bytes(_KEY_BYTES))
            .decode("ascii")
            .rstrip("=")
        )

    def hash(self, raw_key: str) -> ApiKeyHash:
        return ApiKeyHash(self._hasher.hash(raw_key))
