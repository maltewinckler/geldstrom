"""Top-level application factory port."""

from __future__ import annotations

from typing import Protocol

from gateway.application.common import IdProvider
from gateway.domain.banking_gateway import BankingConnector
from gateway.domain.consumer_access import ApiKeyVerifier

from .cache_factory import CacheFactory
from .repository_factory import RepositoryFactory


class ApplicationFactory(Protocol):
    """Cross-cutting factory for all application service dependencies."""

    @property
    def repos(self) -> RepositoryFactory: ...

    @property
    def caches(self) -> CacheFactory: ...

    # --- Crypto ---
    @property
    def api_key_verifier(self) -> ApiKeyVerifier: ...

    # --- Banking ---
    @property
    def banking_connector(self) -> BankingConnector: ...

    # --- Utilities ---
    @property
    def id_provider(self) -> IdProvider: ...

    @property
    def operation_session_ttl_seconds(self) -> int: ...
