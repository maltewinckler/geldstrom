"""Concrete application factory for the gateway backend."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from functools import cached_property
from uuid import uuid4

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine

from gateway.application.audit import AuditService
from gateway.application.common import IdProvider, InternalError
from gateway.application.ports import CacheFactory, RepositoryFactory
from gateway.domain.banking_gateway import BankingConnector
from gateway.infrastructure.banking.geldstrom import GeldstromBankingConnector
from gateway.infrastructure.banking.protocols import BankingConnectorDispatcher
from gateway.infrastructure.cache.memory import (
    InMemoryApiConsumerCache,
    InMemoryFinTSInstituteCache,
    PostgresNotifyListener,
)
from gateway.infrastructure.cache.redis import RedisOperationSessionStore
from gateway.infrastructure.crypto import (
    Argon2ApiKeyService,
)
from gateway.infrastructure.persistence.sqlalchemy import (
    build_engine,
)
from gateway.infrastructure.readiness import SQLGatewayReadinessService

_logger = logging.getLogger(__name__)


class _RuntimeIdProvider(IdProvider):
    def new_operation_id(self) -> str:
        return str(uuid4())

    def now(self) -> datetime:
        return datetime.now(UTC)


class _SQLRepositoryFactory(RepositoryFactory):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    @cached_property
    def consumer(self) -> ApiConsumerRepositorySqlAlchemy:
        return ApiConsumerRepositorySqlAlchemy(self._engine)

    @cached_property
    def institute(self) -> FinTSInstituteRepositorySqlAlchemy:
        return FinTSInstituteRepositorySqlAlchemy(self._engine)

    @cached_property
    def product_registration(self) -> FinTSProductRegistrationRepositorySqlAlchemy:
        return FinTSProductRegistrationRepositorySqlAlchemy(self._engine)


class _GatewayCacheFactory(CacheFactory):
    """Consumer and institute caches in-memory; session store in Redis."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    @cached_property
    def consumer(self) -> InMemoryApiConsumerCache:
        return InMemoryApiConsumerCache()

    @cached_property
    def institute(self) -> InMemoryFinTSInstituteCache:
        return InMemoryFinTSInstituteCache()

    @cached_property
    def session_store(self) -> RedisOperationSessionStore:
        return RedisOperationSessionStore(self._redis)


class GatewayApplicationFactory:
    """Concrete application factory providing all service dependencies."""

    def __init__(self, settings) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._loaded_product_key: str | None = None
        self._redis: Redis | None = None

    @cached_property
    def repos(self) -> _SQLRepositoryFactory:
        return _SQLRepositoryFactory(self._engine)

    @cached_property
    def caches(self) -> _GatewayCacheFactory:
        if self._redis is None:
            raise InternalError("Redis not initialised - call startup() first")
        return _GatewayCacheFactory(self._redis)

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
    def banking_connector(self) -> BankingConnector:
        if self._loaded_product_key is None:
            raise InternalError("Product key not loaded")
        fints_connector = GeldstromBankingConnector(
            self._loaded_product_key,
            product_version=self._settings.fints_product_version,
        )
        return BankingConnectorDispatcher(fints_connector=fints_connector)

    @cached_property
    def id_provider(self) -> _RuntimeIdProvider:
        return _RuntimeIdProvider()

    @property
    def operation_session_ttl_seconds(self) -> int:
        return self._settings.operation_session_ttl_seconds

    @cached_property
    def audit_repository(self) -> AuditRepositorySqlAlchemy:
        return AuditRepositorySqlAlchemy(self._engine)

    @cached_property
    def audit_service(self) -> AuditService:
        return AuditService(self.audit_repository, self.id_provider)

    @cached_property
    def readiness_service(self) -> SQLGatewayReadinessService:
        if self._redis is None:
            raise InternalError("Redis not initialised - call startup() first")
        return SQLGatewayReadinessService(self._engine, self._redis)

    @cached_property
    def _engine(self) -> AsyncEngine:
        return build_engine(self._settings.database_url.get_secret_value())

    @cached_property
    def _notify_listener(self) -> PostgresNotifyListener:
        s = self._settings
        return PostgresNotifyListener(
            database_url=s.database_url.get_secret_value(),
            consumer_repository=self.repos.consumer,
            consumer_cache=self.caches.consumer,
            institute_repository=self.repos.institute,
            institute_cache=self.caches.institute,
            reconnect_backoff_seconds=s.notify_reconnect_backoff_seconds,
        )

    async def startup(self) -> None:
        """Warm all runtime caches and start background workers."""
        await self._connect_redis()
        await self._warm_product_key()
        await self._start_notify_listener()
        await self._warm_consumer_cache()
        await self._warm_institute_cache()
        _logger.info("gateway startup complete")

    async def shutdown(self) -> None:
        """Stop background workers and release database resources."""
        await self._stop_notify_listener()
        await self._close_redis()
        await self._close_db_engine()
        _logger.info("gateway shutdown complete")

    async def _warm_product_key(self) -> None:
        from gateway.application.common import InternalError

        registration = await self.repos.product_registration.get_current()
        if registration is None:
            raise InternalError("No product registration found in the database")
        self._loaded_product_key = registration.product_key
        _logger.info("product key loaded")

    async def _warm_consumer_cache(self) -> None:
        consumers = await self.repos.consumer.list_all_active()
        await self.caches.consumer.load(consumers)
        _logger.info("consumer cache warmed", extra={"count": len(consumers)})

    async def _warm_institute_cache(self) -> None:
        institutes = await self.repos.institute.list_all()
        await self.caches.institute.load(institutes)
        _logger.info("institute cache warmed", extra={"count": len(institutes)})

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

    async def _connect_redis(self) -> None:
        self._redis = Redis.from_url(
            self._settings.redis_url,
            decode_responses=False,
        )
        await self._redis.ping()
        _logger.info("redis connected", extra={"url": self._settings.redis_url})

    async def _close_redis(self) -> None:
        if self._redis is not None:
            try:
                await self._redis.aclose()
                _logger.info("redis connection closed")
            except Exception:
                _logger.warning("error closing redis connection", exc_info=True)
            self._redis = None
