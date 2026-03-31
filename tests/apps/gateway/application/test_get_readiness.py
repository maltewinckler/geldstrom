"""Tests for the GetReadinessQuery application use case."""

from __future__ import annotations

import asyncio

from gateway.application.common import GetReadinessQuery, ReadinessStatus


class FakeReadinessService:
    def __init__(self, status: ReadinessStatus) -> None:
        self._status = status

    async def check(self) -> ReadinessStatus:
        return self._status


def test_get_readiness_returns_ready_when_all_checks_pass() -> None:
    status = ReadinessStatus(db=True, product_key=True, catalog=True)
    result = asyncio.run(GetReadinessQuery(FakeReadinessService(status))())

    assert result is status
    assert result.is_ready is True


def test_get_readiness_is_ready_computed_field_false_when_db_down() -> None:
    status = ReadinessStatus(db=False, product_key=False, catalog=False)
    result = asyncio.run(GetReadinessQuery(FakeReadinessService(status))())

    assert result.is_ready is False
    assert result.db is False


def test_get_readiness_is_ready_false_when_catalog_empty() -> None:
    status = ReadinessStatus(db=True, product_key=True, catalog=False)
    result = asyncio.run(GetReadinessQuery(FakeReadinessService(status))())

    assert result.is_ready is False
    assert result.catalog is False


def test_get_readiness_is_ready_false_when_product_key_missing() -> None:
    status = ReadinessStatus(db=True, product_key=False, catalog=True)
    result = asyncio.run(GetReadinessQuery(FakeReadinessService(status))())

    assert result.is_ready is False
    assert result.product_key is False


def test_readiness_status_is_frozen() -> None:
    status = ReadinessStatus(db=True, product_key=True, catalog=True)
    try:
        status.db = False  # type: ignore[misc]
        raise AssertionError("Expected ValidationError on mutation")
    except Exception as exc:
        assert "frozen" in str(exc).lower() or "immutable" in str(exc).lower()
