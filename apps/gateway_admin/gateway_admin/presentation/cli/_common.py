"""Shared CLI helpers: build the repository and service factories from settings."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from gateway_admin.config import get_settings
from gateway_admin.infrastructure.persistence.sqlalchemy.factories.admin_factory import (
    AdminRepositoryFactorySQLAlchemy,
)
from gateway_admin.infrastructure.persistence.sqlalchemy.factories.service_factory import (
    ServiceFactorySQLAlchemy,
)


@dataclass
class CliContext:
    repo_factory: AdminRepositoryFactorySQLAlchemy
    service_factory: ServiceFactorySQLAlchemy


@asynccontextmanager
async def build_context() -> AsyncIterator[CliContext]:
    repo_factory = AdminRepositoryFactorySQLAlchemy(settings=get_settings())
    try:
        yield CliContext(
            repo_factory=repo_factory,
            service_factory=ServiceFactorySQLAlchemy.from_factory(repo_factory),
        )
    finally:
        await repo_factory.dispose()
