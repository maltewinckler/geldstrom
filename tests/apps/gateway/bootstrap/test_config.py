"""Tests for gateway bootstrap settings and container factories."""

from __future__ import annotations

import fakeredis.aioredis

from gateway.config import Settings
from gateway.infrastructure.cache.memory import (
    PostgresNotifyListener,
)
from gateway.infrastructure.cache.redis import RedisOperationSessionStore
from gateway.infrastructure.crypto import Argon2ApiKeyService
from gateway.infrastructure.gateway_factory import GatewayApplicationFactory
from gateway.presentation.http.dependencies import get_factory, get_settings


def _reset() -> None:
    get_settings.cache_clear()
    get_factory.cache_clear()


def test_settings_load_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("GATEWAY_DB_PASSWORD", "s3cr3t")
    monkeypatch.setenv("GATEWAY_DB_NAME", "mydb")
    monkeypatch.setenv("GATEWAY_ARGON2_TIME_COST", "3")
    _reset()

    settings = get_settings()

    assert settings.database_url.get_secret_value().endswith("/mydb")
    assert settings.argon2_time_cost == 3


def test_settings_apply_default_values(monkeypatch) -> None:
    monkeypatch.setenv("GATEWAY_DB_PASSWORD", "s3cr3t")
    _reset()

    settings = Settings()

    assert settings.argon2_time_cost == 2
    assert settings.argon2_memory_cost == 65_536
    assert settings.argon2_parallelism == 2
    assert settings.operation_session_ttl_seconds == 120
    assert settings.rate_limit_requests_per_minute == 60
    assert settings.notify_reconnect_backoff_seconds == 1.0


def test_factory_is_singleton_and_deps_are_cached(monkeypatch) -> None:
    monkeypatch.setenv("GATEWAY_DB_PASSWORD", "s3cr3t")
    _reset()

    factory = get_factory()
    # Simulate Redis being connected so caches can be instantiated
    factory._redis = fakeredis.aioredis.FakeRedis()

    assert isinstance(factory, GatewayApplicationFactory)
    assert get_factory() is factory
    assert isinstance(factory.caches.session_store, RedisOperationSessionStore)
    assert factory.caches.session_store is factory.caches.session_store
    assert isinstance(factory.api_key_service, Argon2ApiKeyService)
    assert isinstance(factory._notify_listener, PostgresNotifyListener)
