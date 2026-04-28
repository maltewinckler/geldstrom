"""Idempotent database schema initialisation command."""

from __future__ import annotations

from typing import TYPE_CHECKING, Self

from gateway_admin.infrastructure.persistence.sqlalchemy.db_init import (
    initialize_database,
)

if TYPE_CHECKING:
    from gateway_admin.application.factories.admin_factory import AdminRepositoryFactory


class InitializeDatabaseCommand:
    """Ensure the database schema and gateway DB user exist.

    Delegates to the infrastructure layer. Idempotent - safe to call on every
    startup. Does not touch application-level concerns such as product registration.
    """

    def __init__(self, repo_factory: AdminRepositoryFactory) -> None:
        self._repo_factory = repo_factory

    @classmethod
    def from_factory(cls, repo_factory: AdminRepositoryFactory) -> Self:
        return cls(repo_factory)

    async def __call__(self) -> None:
        # directly builds a POSTGRES database. This is a smell because
        # we do not have it baked into the factory. This is a small one-of concern
        # though. So we accept this code smell here.
        await initialize_database(self._repo_factory.settings)
