"""Concrete application factory for the gateway backend."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from functools import cached_property
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from gateway.application.common import IdProvider, InternalError
from gateway.application.health.ports.readiness_check import ReadinessCheck
from gateway.infrastructure.banking.geldstrom import GeldstromBankingConnector
from gateway.infrastructure.cache.memory import (
    InMemoryApiConsumerCache,
    InMemoryCurrentProductKeyProvider,
    InMemoryFinTSInstituteCache,
    InMemoryOperationSessionStore,
    InMemoryProductRegistrationCache,
    PostgresNotifyListener,
)
from gateway.infrastructure.crypto import Argon2ApiKeyService, ProductKeyService
from gateway.infrastructure.persistence.csv.institute_csv_reader import (
    InstituteCsvReader,
)
from gateway.infrastructure.persistence.postgres import (
    PostgresApiConsumerRepository,
    PostgresFinTSInstituteRepository,
    PostgresFinTSProductRegistrationRepository,
    build_engine,
)

_logger = logging.getLogger(__name__)


class _RuntimeIdProvider(IdProvider):
    def new_operation_id(self) -> str:
        return str(uuid4())

    def now(self) -> datetime:
        return datetime.now(UTC)


class _SQLAlchemyRepositoryFactory:
    """Repository implementations backed by SQLAlchemy / PostgreSQL."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    @cached_property
    def consumer(self) -> PostgresApiConsumerRepository:
        return PostgresApiConsumerRepository(self._engine)

    @cached_property
    def institute(self) -> PostgresFinTSInstituteRepository:
        return PostgresFinTSInstituteRepository(self._engine)

    @cached_property
    def product_registration(self) -> PostgresFinTSProductRegistrationRepository:
        return PostgresFinTSProductRegistrationRepository(self._engine)


class _InMemoryCacheFactory:
    """Cache implementations backed by in-memory data structures."""

    def __init__(self, max_sessions: int) -> None:
        self._max_sessions = max_sessions

    @cached_property
    def consumer(self) -> InMemoryApiConsumerCache:
        return InMemoryApiConsumerCache()

    @cached_property
    def institute(self) -> InMemoryFinTSInstituteCache:
        return InMemoryFinTSInstituteCache()

    @cached_property
    def product_key(self) -> InMemoryCurrentProductKeyProvider:
        return InMemoryCurrentProductKeyProvider()

    @cached_property
    def product_registration(self) -> InMemoryProductRegistrationCache:
        return InMemoryProductRegistrationCache()

    @cached_property
    def session_store(self) -> InMemoryOperationSessionStore:
        return InMemoryOperationSessionStore(max_sessions=self._max_sessions)


class GatewayApplicationFactory:
    """Concrete factory providing all application service dependencies.

    Implements the ApplicationFactory protocol.
    Owns the PostgresNotifyListener and database engine lifecycle.
    """

    def __init__(self, settings) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings

    # ---------- Sub-factories ----------
    @cached_property
    def repos(self) -> _SQLAlchemyRepositoryFactory:
        return _SQLAlchemyRepositoryFactory(self._engine)

    @cached_property
    def caches(self) -> _InMemoryCacheFactory:
        return _InMemoryCacheFactory(self._settings.operation_session_max_count)

    # ---------- Crypto ----------
    @cached_property
    def api_key_service(self) -> Argon2ApiKeyService:
        s = self._settings
        return Argon2ApiKeyService(
            time_cost=s.argon2_time_cost,
            memory_cost=s.argon2_memory_cost,
            parallelism=s.argon2_parallelism,
        )

    @property
    def api_key_verifier(self) -> Argon2ApiKeyService:
        return self.api_key_service

    @cached_property
    def _product_key_service(self) -> ProductKeyService:
        return ProductKeyService(self._settings.product_master_key.get_secret_value())

    @property
    def product_key_encryptor(self) -> ProductKeyService:
        return self._product_key_service

    # ---------- Banking ----------
    @cached_property
    def banking_connector(self) -> GeldstromBankingConnector:
        return GeldstromBankingConnector(
            self.caches.product_key,
            product_version=self._settings.fints_product_version,
        )

    # ---------- Utilities ----------
    @cached_property
    def id_provider(self) -> _RuntimeIdProvider:
        return _RuntimeIdProvider()

    @cached_property
    def institute_csv_reader(self) -> InstituteCsvReader:
        return InstituteCsvReader()

    # ---------- Health ----------
    @property
    def readiness_checks(self) -> Mapping[str, ReadinessCheck]:
        return {
            "postgres": self._check_postgres,
            "consumer_cache": self._check_consumer_cache,
            "institute_cache": self._check_institute_cache,
            "product_registration_cache": self._check_product_registration_cache,
            "product_key_material": self._check_product_key_material,
            "operation_session_runtime": self._check_operation_session_runtime,
        }

    # ---------- Private: engine ----------
    @cached_property
    def _engine(self) -> AsyncEngine:
        return build_engine(self._settings.database_url.get_secret_value())

    # ---------- Private: notify listener ----------
    @cached_property
    def _notify_listener(self) -> PostgresNotifyListener:
        s = self._settings
        return PostgresNotifyListener(
            database_url=s.database_url.get_secret_value(),
            consumer_repository=self.repos.consumer,
            consumer_cache=self.caches.consumer,
            institute_repository=self.repos.institute,
            institute_cache=self.caches.institute,
            product_registration_repository=self.repos.product_registration,
            product_registration_cache=self.caches.product_registration,
            reconnect_backoff_seconds=s.notify_reconnect_backoff_seconds,
        )

    # ---------- Health check implementations ----------
    async def _check_postgres(self) -> bool:
        try:
            async with self._engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except Exception:
            return False
        return True

    async def _check_consumer_cache(self) -> bool:
        await self.caches.consumer.list_active()
        return True

    async def _check_institute_cache(self) -> bool:
        return self.caches.institute is not None

    async def _check_product_registration_cache(self) -> bool:
        return self.caches.product_registration is not None

    async def _check_product_key_material(self) -> bool:
        try:
            await self.caches.product_key.require_current()
        except InternalError:
            return False
        return True

    async def _check_operation_session_runtime(self) -> bool:
        return self.caches.session_store is not None

    # ---------- Lifecycle ----------
    async def startup(self) -> None:
        """Warm all runtime caches and start background workers."""
        await self._warm_consumer_cache()
        await self._warm_institute_cache()
        await self._warm_product_registration()
        await self._start_notify_listener()
        _logger.info("gateway startup complete")

    async def shutdown(self) -> None:
        """Stop background workers and release database resources."""
        await self._stop_notify_listener()
        await self._close_db_engine()
        _logger.info("gateway shutdown complete")

    async def _warm_consumer_cache(self) -> None:
        consumers = await self.repos.consumer.list_all_active()
        await self.caches.consumer.load(consumers)
        _logger.info("consumer cache warmed", extra={"count": len(consumers)})

    async def _warm_institute_cache(self) -> None:
        institutes = await self.repos.institute.list_all()
        await self.caches.institute.load(institutes)
        _logger.info("institute cache warmed", extra={"count": len(institutes)})

    async def _warm_product_registration(self) -> None:
        registration = await self.repos.product_registration.get_current()
        await self.caches.product_registration.set_current(registration)
        if registration is not None:
            try:
                plaintext = self._product_key_service.decrypt(
                    registration.encrypted_product_key
                )
                await self.caches.product_key.load_current(plaintext)
                _logger.info("product key material loaded")
            except Exception:
                _logger.warning(
                    "product key decryption failed during startup — "
                    "readiness check will report not_ready"
                )
        else:
            _logger.info(
                "no product registration found — readiness check will report not_ready"
            )

    async def _start_notify_listener(self) -> None:
        await self._notify_listener.start()
        _logger.info("postgres notify listener started")

    async def _stop_notify_listener(self) -> None:
        try:
            await self._notify_listener.stop()
            _logger.info("postgres notify listener stopped")
        except Exception:
            _logger.warning("error stopping notify listener", exc_info=True)

    async def _close_db_engine(self) -> None:
        try:
            await self._engine.dispose()
            _logger.info("database engine disposed")
        except Exception:
            _logger.warning("error disposing database engine", exc_info=True)
