"""Top-level application factory port."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from gateway.application.common import IdProvider
from gateway.application.ports.cache_factory import CacheFactory
from gateway.application.ports.gateway_readiness_service import GatewayReadinessPort
from gateway.application.ports.repository_factory import RepositoryFactory
from gateway.domain.banking_gateway import BankingConnector
from gateway.domain.consumer_access import ApiKeyVerifier

if TYPE_CHECKING:
    from gateway.application.audit import AuditService


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

    @property
    def audit_service(self) -> AuditService: ...
