"""Domain service protocols for consumer access."""

from __future__ import annotations

from typing import Protocol

from gateway.domain.consumer_access.value_objects import ApiKeyHash


class ApiKeyVerifier(Protocol):
    """Verifies a presented API key against a stored password-grade hash."""

    def verify(self, presented_key: str, stored_hash: ApiKeyHash) -> bool: ...
