"""SQLAlchemy implementation of AdminRepositoryFactory."""

from __future__ import annotations

from functools import cached_property

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from gateway_admin.config import Settings, get_settings
from gateway_admin.infrastructure.persistence.sqlalchemy.repositories.audit_repository import (
    AuditRepositorySqlAlchemy,
)
from gateway_admin.infrastructure.persistence.sqlalchemy.repositories.institute_repository import (
    InstituteRepositorySQLAlchemy,
)
from gateway_admin.infrastructure.persistence.sqlalchemy.repositories.product_repository import (
    ProductRegistrationRepositorySQLAlchemy,
)
from gateway_admin.infrastructure.persistence.sqlalchemy.repositories.user_repository import (
    UserRepositorySQLAlchemy,
)


class AdminRepositoryFactorySQLAlchemy:
    """Provides Postgres/SQLAlchemy repositories and application settings.

    This is the only persistence abstraction. Commands, queries, and services
    receive an instance of this class (typed as AdminRepositoryFactory).
    Services build themselves via their own ``from_factory(repo_factory)``
    classmethods, reading configuration from ``repo_factory.settings``.

    Satisfies: AdminRepositoryFactory
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def settings(self) -> Settings:
        return self._settings

    @cached_property
    def _engine(self) -> AsyncEngine:
        return create_async_engine(self._settings.database_url)

    @cached_property
    def users(self) -> UserRepositorySQLAlchemy:
        return UserRepositorySQLAlchemy(self._engine)

    @cached_property
    def institutes(self) -> InstituteRepositorySQLAlchemy:
        return InstituteRepositorySQLAlchemy(self._engine)

    @cached_property
    def product_registration(self) -> ProductRegistrationRepositorySQLAlchemy:
        return ProductRegistrationRepositorySQLAlchemy(self._engine)

    @cached_property
    def audit(self) -> AuditRepositorySqlAlchemy:
        return AuditRepositorySqlAlchemy(self._engine)

    async def dispose(self) -> None:
        """Dispose the underlying SQLAlchemy engine."""
        await self._engine.dispose()
