"""Unit tests for AuditService."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID

from gateway.application.audit.audit_service import AuditService
from gateway.domain.audit import AuditEvent, AuditEventType
from tests.apps.gateway.fakes import FakeIdProvider

_CONSUMER_ID = UUID("12345678-1234-5678-1234-567812345678")
_OPERATION_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


def _make_service(repo: AsyncMock) -> AuditService:
    id_provider = FakeIdProvider(
        now_value=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        operation_ids=[_OPERATION_ID],
    )
    return AuditService(repo=repo, id_provider=id_provider)


def test_record_calls_repo_append_with_correct_event_type_and_consumer_id() -> None:
    repo = AsyncMock()
    service = _make_service(repo)

    asyncio.run(service.record(AuditEventType.CONSUMER_AUTHENTICATED, _CONSUMER_ID))

    repo.append.assert_awaited_once()
    event: AuditEvent = repo.append.call_args[0][0]
    assert event.event_type == AuditEventType.CONSUMER_AUTHENTICATED
    assert event.consumer_id == _CONSUMER_ID


def test_record_calls_repo_append_with_none_consumer_id_for_unknown_key() -> None:
    repo = AsyncMock()
    service = _make_service(repo)

    asyncio.run(service.record(AuditEventType.CONSUMER_AUTH_FAILED, None))

    repo.append.assert_awaited_once()
    event: AuditEvent = repo.append.call_args[0][0]
    assert event.event_type == AuditEventType.CONSUMER_AUTH_FAILED
    assert event.consumer_id is None


def test_record_does_not_reraise_when_repo_raises() -> None:
    repo = AsyncMock()
    repo.append.side_effect = RuntimeError("DB unavailable")
    service = _make_service(repo)

    # Should not raise — audit failures are fire-and-forget
    asyncio.run(service.record(AuditEventType.CONSUMER_AUTHENTICATED, _CONSUMER_ID))
