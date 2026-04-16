"""API key service abstract base class."""

from __future__ import annotations

from abc import ABC, abstractmethod

from gateway_admin.domain.value_objects.user import ApiKeyHash


class AdminApiKeyService(ABC):
    @abstractmethod
    def generate(self, consumer_id: str) -> str: ...

    @abstractmethod
    def hash(self, raw_key: str) -> ApiKeyHash: ...
