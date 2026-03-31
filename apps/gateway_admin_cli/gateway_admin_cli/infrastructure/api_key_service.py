"""Argon2 API key service for the admin CLI (generate+hash only)."""

from __future__ import annotations

import secrets

from argon2 import PasswordHasher

from gateway_admin_cli.domain.users import ApiKeyHash

_KEY_BYTES = 32


class Argon2AdminApiKeyService:
    """Generates cryptographically secure API keys and hashes them with Argon2id.

    Keys are prefixed with the first 8 hex characters of the consumer UUID
    so the gateway can perform O(1) consumer lookup before running Argon2.
    Format: ``{prefix}.{token}``
    """

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

    def generate(self, consumer_id: str) -> str:
        prefix = consumer_id.replace("-", "")[:8]
        token = secrets.token_urlsafe(_KEY_BYTES)
        return f"{prefix}.{token}"

    def hash(self, raw_key: str) -> ApiKeyHash:
        return ApiKeyHash(self._hasher.hash(raw_key))
