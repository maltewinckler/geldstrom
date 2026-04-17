"""AdminRepositoryFactory port - the single persistence abstraction."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from gateway_admin.domain.audit.repository import AuditQueryRepository
from gateway_admin.domain.repositories import (
    AdminInstituteRepository,
    ProductRegistrationRepository,
    UserRepository,
)

if TYPE_CHECKING:
    from gateway_admin.config import Settings


@runtime_checkable
class AdminRepositoryFactory(Protocol):
    """Provides repository instances and application settings for the admin CLI.

    Commands, queries, and services depend on this protocol; concrete
    implementations live in the infrastructure layer.
    """

    @property
    def settings(self) -> Settings: ...

    @property
    def users(self) -> UserRepository: ...

    @property
    def institutes(self) -> AdminInstituteRepository: ...

    @property
    def product_registration(self) -> ProductRegistrationRepository: ...

    @property
    def audit(self) -> AuditQueryRepository: ...
