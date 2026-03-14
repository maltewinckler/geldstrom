"""Tests for the ResumePendingOperations use case."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from gateway.application.banking.commands.resume_pending_operations import (
    ResumePendingOperationsCommand,
)
from gateway.domain.banking_gateway import (
    OperationStatus,
    PendingOperationSession,
    ResumeResult,
)
from gateway.domain.consumer_access import ConsumerId
from gateway.domain.shared import BankProtocol
from tests.apps.gateway.fakes import (
    FakeBankingConnector,
    FakeIdProvider,
    FakeOperationSessionStore,
)


def test_resume_pending_operations_transitions_pending_to_completed() -> None:
    now = datetime(2026, 3, 7, 12, 0, tzinfo=UTC)
    session_store = FakeOperationSessionStore([_session("op-1", now=now)])
    use_case = ResumePendingOperationsCommand(
        session_store=session_store,
        connector=FakeBankingConnector(
            resume_results=[
                ResumeResult(
                    status=OperationStatus.COMPLETED,
                    result_payload={"accounts": [{"iban": "DE89370400440532013000"}]},
                )
            ]
        ),
        id_provider=FakeIdProvider(now_value=now, operation_ids=["unused"]),
    )

    summary = asyncio.run(use_case())
    stored_session = asyncio.run(session_store.get("op-1"))

    assert summary.completed_count == 1
    assert stored_session is not None
    assert stored_session.status is OperationStatus.COMPLETED
    assert stored_session.session_state == b"cleared"
    assert stored_session.result_payload == {
        "accounts": [{"iban": "DE89370400440532013000"}]
    }


def test_resume_pending_operations_transitions_pending_to_failed() -> None:
    now = datetime(2026, 3, 7, 12, 0, tzinfo=UTC)
    session_store = FakeOperationSessionStore([_session("op-1", now=now)])
    use_case = ResumePendingOperationsCommand(
        session_store=session_store,
        connector=FakeBankingConnector(
            resume_results=[
                ResumeResult(
                    status=OperationStatus.FAILED,
                    failure_reason="bank rejected confirmation",
                )
            ]
        ),
        id_provider=FakeIdProvider(now_value=now, operation_ids=["unused"]),
    )

    summary = asyncio.run(use_case())
    stored_session = asyncio.run(session_store.get("op-1"))

    assert summary.failed_count == 1
    assert stored_session is not None
    assert stored_session.status is OperationStatus.FAILED
    assert stored_session.session_state == b"cleared"
    assert stored_session.failure_reason == "bank rejected confirmation"


def test_resume_pending_operations_transitions_pending_to_expired() -> None:
    now = datetime(2026, 3, 7, 12, 0, tzinfo=UTC)
    session_store = FakeOperationSessionStore(
        [
            _session(
                "op-1",
                now=now - timedelta(minutes=10),
                expires_at=now - timedelta(minutes=1),
            )
        ]
    )
    use_case = ResumePendingOperationsCommand(
        session_store=session_store,
        connector=FakeBankingConnector(),
        id_provider=FakeIdProvider(now_value=now, operation_ids=["unused"]),
    )

    summary = asyncio.run(use_case())
    stored_session = asyncio.run(session_store.get("op-1"))

    assert summary.expired_count == 1
    assert stored_session is not None
    assert stored_session.status is OperationStatus.EXPIRED
    assert stored_session.session_state == b"cleared"


def _session(
    operation_id: str,
    *,
    now: datetime,
    expires_at: datetime | None = None,
) -> PendingOperationSession:
    return PendingOperationSession(
        operation_id=operation_id,
        consumer_id=ConsumerId(UUID("12345678-1234-5678-1234-567812345678")),
        protocol=BankProtocol.FINTS,
        operation_type="accounts",
        session_state=b"opaque-state",
        status=OperationStatus.PENDING_CONFIRMATION,
        created_at=now,
        expires_at=expires_at or (now + timedelta(minutes=5)),
    )
