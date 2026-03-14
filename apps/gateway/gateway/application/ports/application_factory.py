"""Top-level application factory port."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from gateway.application.administration.ports.api_key_service import ApiKeyService
from gateway.application.administration.ports.institute_csv_reader import (
    InstituteCsvReaderPort,
)
from gateway.application.administration.ports.product_key_encryptor import (
    ProductKeyEncryptor,
)
from gateway.application.common import IdProvider
from gateway.application.health.ports.readiness_check import ReadinessCheck
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
    def api_key_service(self) -> ApiKeyService: ...

    @property
    def api_key_verifier(self) -> ApiKeyVerifier: ...

    @property
    def product_key_encryptor(self) -> ProductKeyEncryptor: ...

    # --- Banking ---
    @property
    def banking_connector(self) -> BankingConnector: ...

    # --- Utilities ---
    @property
    def id_provider(self) -> IdProvider: ...

    @property
    def institute_csv_reader(self) -> InstituteCsvReaderPort: ...

    # --- Health ---
    @property
    def readiness_checks(self) -> Mapping[str, ReadinessCheck]: ...
