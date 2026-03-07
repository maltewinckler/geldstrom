"""Unit tests for LogAuditEventPublisher.

Tests structured log output, fire-and-forget semantics, and error suppression.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import pytest

from gateway.domain.banking.value_objects.connection import BankingProtocol
from gateway.domain.session.value_objects.audit import AuditEvent
from gateway.infrastructure.session.audit_publisher import LogAuditEventPublisher


@pytest.fixture
def publisher() -> LogAuditEventPublisher:
    return LogAuditEventPublisher()


def _make_event(
    protocol: BankingProtocol | None = BankingProtocol.FINTS,
) -> AuditEvent:
    return AuditEvent(
        timestamp=datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC),
        account_id="acct-123",
        remote_ip="192.168.1.1",
        request_type="/v1/transactions/fetch",
        protocol=protocol,
    )


@pytest.mark.asyncio
async def test_publish_logs_at_info_level(
    publisher: LogAuditEventPublisher,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """publish() should emit an INFO-level log entry."""
    with caplog.at_level(logging.INFO, logger="gateway.audit"):
        await publisher.publish(_make_event())

    assert len(caplog.records) == 1
    assert caplog.records[0].levelno == logging.INFO


@pytest.mark.asyncio
async def test_publish_includes_all_fields_in_extra(
    publisher: LogAuditEventPublisher,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """publish() should include all AuditEvent fields as structured extra data."""
    event = _make_event()
    with caplog.at_level(logging.INFO, logger="gateway.audit"):
        await publisher.publish(event)

    record = caplog.records[0]
    assert record.timestamp == "2024-06-15T12:00:00+00:00"
    assert record.account_id == "acct-123"
    assert record.remote_ip == "192.168.1.1"
    assert record.request_type == "/v1/transactions/fetch"
    assert record.protocol == "fints"


@pytest.mark.asyncio
async def test_publish_with_none_protocol(
    publisher: LogAuditEventPublisher,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """publish() should handle None protocol gracefully."""
    event = _make_event(protocol=None)
    with caplog.at_level(logging.INFO, logger="gateway.audit"):
        await publisher.publish(event)

    record = caplog.records[0]
    assert record.protocol is None


@pytest.mark.asyncio
async def test_publish_message_is_audit_event(
    publisher: LogAuditEventPublisher,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """publish() should use 'audit_event' as the log message."""
    with caplog.at_level(logging.INFO, logger="gateway.audit"):
        await publisher.publish(_make_event())

    assert caplog.records[0].message == "audit_event"


@pytest.mark.asyncio
async def test_publish_never_raises_on_error(
    publisher: LogAuditEventPublisher,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """publish() should never raise — errors are caught and logged at WARNING."""
    logger = logging.getLogger("gateway.audit")

    def _boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("logging exploded")

    monkeypatch.setattr(logger, "info", _boom)

    # Should not raise
    await publisher.publish(_make_event())


@pytest.mark.asyncio
async def test_publish_logs_warning_on_error(
    publisher: LogAuditEventPublisher,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """publish() should log a WARNING when the info log call fails."""
    logger = logging.getLogger("gateway.audit")

    def _boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("logging exploded")

    monkeypatch.setattr(logger, "info", _boom)

    with caplog.at_level(logging.WARNING, logger="gateway.audit"):
        await publisher.publish(_make_event())

    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warning_records) == 1
    assert "Failed to publish audit event" in warning_records[0].message


@pytest.mark.asyncio
async def test_publish_satisfies_audit_event_publisher_protocol() -> None:
    """LogAuditEventPublisher should satisfy AuditEventPublisher protocol."""
    from gateway.domain.ports import AuditEventPublisher

    publisher = LogAuditEventPublisher()
    assert isinstance(publisher, AuditEventPublisher)
