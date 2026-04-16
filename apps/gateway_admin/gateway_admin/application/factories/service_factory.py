"""ServiceFactory port - the single service abstraction."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from gateway_admin.domain.services.api_key import AdminApiKeyService
from gateway_admin.domain.services.email import EmailService
from gateway_admin.domain.services.gateway_notifications import (
    GatewayNotificationService,
)
from gateway_admin.domain.services.identity import IdProvider
from gateway_admin.domain.services.institute_csv import InstituteCsvReaderPort


@runtime_checkable
class ServiceFactory(Protocol):
    """Provides all application service instances.

    Commands and queries depend on this protocol; concrete implementations
    live in the infrastructure layer.
    """

    @property
    def gateway_notifications(self) -> GatewayNotificationService: ...

    @property
    def email_service(self) -> EmailService: ...

    @property
    def api_key_service(self) -> AdminApiKeyService: ...

    @property
    def id_provider(self) -> IdProvider: ...

    @property
    def csv_reader(self) -> InstituteCsvReaderPort: ...
