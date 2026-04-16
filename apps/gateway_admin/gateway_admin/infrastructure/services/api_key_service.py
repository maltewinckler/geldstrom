"""Argon2id API key service - implements AdminApiKeyService port."""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING, Self

from argon2 import PasswordHasher

from gateway_admin.domain.services.api_key import AdminApiKeyService
from gateway_admin.domain.value_objects.user import ApiKeyHash

if TYPE_CHECKING:
    from gateway_admin.application.factories.admin_factory import AdminRepositoryFactory

_KEY_BYTES = 32


class Argon2AdminApiKeyService(AdminApiKeyService):
    """Generates API keys (``{prefix}.{token}``) and hashes them with Argon2id."""

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

    @classmethod
    def from_factory(cls, repo_factory: AdminRepositoryFactory) -> Self:
        s = repo_factory.settings
        return cls(
            time_cost=s.admin_argon2_time_cost,
            memory_cost=s.admin_argon2_memory_cost,
            parallelism=s.admin_argon2_parallelism,
        )

    def generate(self, consumer_id: str) -> str:
        prefix = consumer_id.replace("-", "")[:8]
        token = secrets.token_urlsafe(_KEY_BYTES)
        return f"{prefix}.{token}"

    def hash(self, raw_key: str) -> ApiKeyHash:
        return ApiKeyHash(self._hasher.hash(raw_key))
