"""SQLAlchemy-backed implementation of ServiceFactory."""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Self

from gateway_admin.application.factories.service_factory import ServiceFactory
from gateway_admin.domain.services.api_key import AdminApiKeyService
from gateway_admin.domain.services.email import EmailService
from gateway_admin.domain.services.gateway_notifications import (
    GatewayNotificationService,
)
from gateway_admin.domain.services.identity import IdProvider
from gateway_admin.domain.services.institute_csv import (
    InstituteCsvReaderPort,
)
from gateway_admin.infrastructure.persistence.sqlalchemy.services.gateway_notifications import (
    GatewayNotificationServiceSQLAlchemy,
)
from gateway_admin.infrastructure.services.api_key_service import (
    Argon2AdminApiKeyService,
)
from gateway_admin.infrastructure.services.email_service import SmtpEmailService
from gateway_admin.infrastructure.services.id_provider import RuntimeIdProvider
from gateway_admin.infrastructure.services.institute_csv_reader import (
    InstituteCsvReader,
)

if TYPE_CHECKING:
    from gateway_admin.application.factories.admin_factory import AdminRepositoryFactory


class ServiceFactorySQLAlchemy(ServiceFactory):
    """Provides all production service instances built from the repository factory.

    Satisfies: ServiceFactory
    """

    def __init__(self, repo_factory: AdminRepositoryFactory) -> None:
        self._repo_factory = repo_factory

    @classmethod
    def from_factory(cls, repo_factory: AdminRepositoryFactory) -> Self:
        return cls(repo_factory)

    @cached_property
    def gateway_notifications(self) -> GatewayNotificationService:
        return GatewayNotificationServiceSQLAlchemy.from_factory(self._repo_factory)

    @cached_property
    def email_service(self) -> EmailService:
        return SmtpEmailService.from_factory(self._repo_factory)

    @cached_property
    def api_key_service(self) -> AdminApiKeyService:
        return Argon2AdminApiKeyService.from_factory(self._repo_factory)

    @cached_property
    def id_provider(self) -> IdProvider:
        return RuntimeIdProvider.from_factory(self._repo_factory)

    @cached_property
    def csv_reader(self) -> InstituteCsvReaderPort:
        return InstituteCsvReader.from_factory(self._repo_factory)
