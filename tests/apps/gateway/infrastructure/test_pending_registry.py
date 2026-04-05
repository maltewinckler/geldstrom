"""Tests for the in-memory PendingClientRegistry."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from gateway.domain.banking_gateway.operations import OperationType
from gateway.infrastructure.banking.geldstrom.registry import (
    PendingClientRegistry,
    PendingHandle,
)


def _make_handle(
    *,
    operation_type: OperationType = OperationType.TRANSACTIONS,
    offset_minutes: int = 5,
) -> PendingHandle:
    client = MagicMock()
    return PendingHandle(
        client=client,
        operation_type=operation_type,
        expires_at=datetime.now(UTC) + timedelta(minutes=offset_minutes),
    )


def test_store_and_get() -> None:
    registry = PendingClientRegistry()
    handle = _make_handle()
    registry.store("h1", handle)
    assert registry.get("h1") is handle


def test_get_unknown_returns_none() -> None:
    registry = PendingClientRegistry()
    assert registry.get("nonexistent") is None


def test_remove_returns_handle_and_calls_cleanup() -> None:
    registry = PendingClientRegistry()
    handle = _make_handle()
    registry.store("h1", handle)

    removed = registry.remove("h1")

    assert removed is handle
    handle.client.cleanup_pending.assert_called_once()
    assert registry.get("h1") is None


def test_remove_unknown_returns_none() -> None:
    registry = PendingClientRegistry()
    assert registry.remove("nonexistent") is None


def test_cleanup_expired_removes_old_handles() -> None:
    registry = PendingClientRegistry()
    expired_handle = _make_handle(offset_minutes=-1)
    active_handle = _make_handle(offset_minutes=5)

    registry.store("expired", expired_handle)
    registry.store("active", active_handle)

    count = registry.cleanup_expired(datetime.now(UTC))

    assert count == 1
    assert registry.get("expired") is None
    assert registry.get("active") is active_handle
    expired_handle.client.cleanup_pending.assert_called_once()


def test_cleanup_expired_returns_zero_when_nothing_expired() -> None:
    registry = PendingClientRegistry()
    registry.store("h1", _make_handle(offset_minutes=5))
    assert registry.cleanup_expired(datetime.now(UTC)) == 0
