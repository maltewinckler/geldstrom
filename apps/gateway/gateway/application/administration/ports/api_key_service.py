"""API key generation and hashing port."""

from __future__ import annotations

from typing import Protocol

from gateway.domain.consumer_access import ApiKeyHash


class ApiKeyService(Protocol):
    """Generates and hashes raw API keys."""

    def generate(self) -> str: ...

    def hash(self, raw_key: str) -> ApiKeyHash: ...
