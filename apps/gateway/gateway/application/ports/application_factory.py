"""Top-level application factory port."""

from __future__ import annotations

from typing import Protocol

from gateway.application.common import IdProvider
from gateway.domain.banking_gateway import BankingConnector
from gateway.domain.consumer_access import ApiKeyVerifier

from .cache_factory import CacheFactory
from .gateway_readiness_service import GatewayReadinessPort
from .repository_factory import RepositoryFactory


class ApplicationFactory(Protocol):
    """Cross-cutting factory for all application service dependencies."""

    @property
    def repos(self) -> RepositoryFactory: ...

    @property
    def caches(self) -> CacheFactory: ...

    @property
    def api_key_verifier(self) -> ApiKeyVerifier: ...

    @property
    def banking_connector(self) -> BankingConnector: ...

    @property
    def id_provider(self) -> IdProvider: ...

    @property
    def operation_session_ttl_seconds(self) -> int: ...

    @property
    def readiness_service(self) -> GatewayReadinessPort: ...
