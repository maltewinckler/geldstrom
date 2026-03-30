"""Tests for gateway bootstrap settings and container factories."""

from __future__ import annotations

from gateway.config import Settings
from gateway.infrastructure.cache.memory import (
    InMemoryApiConsumerCache,
    InMemoryOperationSessionStore,
    PostgresNotifyListener,
)
from gateway.infrastructure.crypto import Argon2ApiKeyService
from gateway.infrastructure.gateway_factory import GatewayApplicationFactory
from gateway.presentation.http.dependencies import get_factory, get_settings


def _reset() -> None:
    get_settings.cache_clear()
    get_factory.cache_clear()


def test_settings_load_from_environment(monkeypatch) -> None:
    monkeypatch.setenv(
        "GATEWAY_DATABASE_URL",
        "postgresql+asyncpg://gateway:secret@localhost:5432/gateway",
    )
    monkeypatch.setenv("GATEWAY_ARGON2_TIME_COST", "3")
    _reset()

    settings = get_settings()

    assert settings.database_url.get_secret_value().endswith("/gateway")
    assert settings.argon2_time_cost == 3


def test_settings_apply_default_values(monkeypatch) -> None:
    monkeypatch.setenv(
        "GATEWAY_DATABASE_URL",
        "postgresql+asyncpg://gateway:secret@localhost:5432/gateway",
    )
    _reset()

    settings = Settings()

    assert settings.argon2_time_cost == 2
    assert settings.argon2_memory_cost == 65_536
    assert settings.argon2_parallelism == 2
    assert settings.operation_session_ttl_seconds == 120
    assert settings.operation_session_max_count == 10_000
    assert settings.rate_limit_requests_per_minute == 60
    assert settings.notify_reconnect_backoff_seconds == 1.0
    assert settings.fints_product_version == "1.0.0"


def test_factory_is_singleton_and_deps_are_cached(monkeypatch) -> None:
    monkeypatch.setenv(
        "GATEWAY_DATABASE_URL",
        "postgresql+asyncpg://gateway:secret@localhost:5432/gateway",
    )
    _reset()

    factory = get_factory()

    assert isinstance(factory, GatewayApplicationFactory)
    assert get_factory() is factory
    assert isinstance(factory.caches.consumer, InMemoryApiConsumerCache)
    assert factory.caches.consumer is factory.caches.consumer
    assert isinstance(factory.caches.session_store, InMemoryOperationSessionStore)
    assert factory.caches.session_store is factory.caches.session_store
    assert isinstance(factory.api_key_service, Argon2ApiKeyService)
    assert isinstance(factory._notify_listener, PostgresNotifyListener)
