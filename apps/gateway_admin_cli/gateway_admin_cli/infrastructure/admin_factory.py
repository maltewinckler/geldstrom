"""Concrete application factory for the admin CLI."""

from __future__ import annotations

from datetime import UTC, datetime
from functools import cached_property
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from gateway_admin_cli.infrastructure.api_key_service import Argon2AdminApiKeyService
from gateway_admin_cli.infrastructure.institute_csv_reader import InstituteCsvReader
from gateway_admin_cli.infrastructure.institute_repository import (
    PostgresAdminInstituteRepository,
)
from gateway_admin_cli.infrastructure.notify_publishers import (
    PostgresInstituteCacheLoader,
    PostgresProductRegistrationNotifier,
    PostgresUserCacheWriter,
)
from gateway_admin_cli.infrastructure.product_repository import (
    PostgresProductRegistrationRepository,
)
from gateway_admin_cli.infrastructure.user_repository import PostgresUserRepository


class _RuntimeIdProvider:
    def new_operation_id(self) -> str:
        return str(uuid4())

    def now(self) -> datetime:
        return datetime.now(UTC)


class _AdminRepositoryFactory:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    @cached_property
    def users(self) -> PostgresUserRepository:
        return PostgresUserRepository(self._engine)

    @cached_property
    def institutes(self) -> PostgresAdminInstituteRepository:
        return PostgresAdminInstituteRepository(self._engine)

    @cached_property
    def product_registration(self) -> PostgresProductRegistrationRepository:
        return PostgresProductRegistrationRepository(self._engine)


class ConcreteAdminFactory:
    """Provides all dependencies for the admin CLI application layer."""

    def __init__(
        self,
        *,
        database_url: str,
        argon2_time_cost: int = 2,
        argon2_memory_cost: int = 65536,
        argon2_parallelism: int = 1,
    ) -> None:
        self._database_url = database_url
        self._argon2_time_cost = argon2_time_cost
        self._argon2_memory_cost = argon2_memory_cost
        self._argon2_parallelism = argon2_parallelism

    @cached_property
    def _engine(self) -> AsyncEngine:
        return create_async_engine(self._database_url)

    @cached_property
    def repos(self) -> _AdminRepositoryFactory:
        return _AdminRepositoryFactory(self._engine)

    @cached_property
    def api_key_service(self) -> Argon2AdminApiKeyService:
        return Argon2AdminApiKeyService(
            time_cost=self._argon2_time_cost,
            memory_cost=self._argon2_memory_cost,
            parallelism=self._argon2_parallelism,
        )

    @cached_property
    def id_provider(self) -> _RuntimeIdProvider:
        return _RuntimeIdProvider()

    @cached_property
    def institute_csv_reader(self) -> InstituteCsvReader:
        return InstituteCsvReader()

    @cached_property
    def user_cache_writer(self) -> PostgresUserCacheWriter:
        return PostgresUserCacheWriter(self._engine)

    @cached_property
    def institute_cache_loader(self) -> PostgresInstituteCacheLoader:
        return PostgresInstituteCacheLoader(self._engine)

    @cached_property
    def product_registration_notifier(self) -> PostgresProductRegistrationNotifier:
        return PostgresProductRegistrationNotifier(self._engine)

    async def dispose(self) -> None:
        """Release database engine resources."""
        await self._engine.dispose()
