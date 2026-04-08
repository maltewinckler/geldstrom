"""Tests for the PollOperationCommand use case."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from gateway.application.banking.commands.poll_operation import (
    PollOperationCommand,
    PollOperationInput,
)
from gateway.application.common import InstitutionNotFoundError
from gateway.application.consumer.queries.authenticate_consumer import (
    AuthenticateConsumerQuery,
)
from gateway.domain.banking_gateway import (
    BankLeitzahl,
    BankProtocol,
    OperationStatus,
    OperationType,
    PendingOperationSession,
    ResumeResult,
)
from gateway.domain.consumer_access import (
    ApiConsumer,
    ApiKeyHash,
    ConsumerStatus,
)
from tests.apps.gateway.fakes import (
    FakeBankingConnector,
    FakeConsumerCache,
    FakeIdProvider,
    FakeOperationSessionStore,
)


class StubApiKeyVerifier:
    def verify(self, presented_key: str, stored_hash: ApiKeyHash) -> bool:
        return presented_key == stored_hash.value


_NOW = datetime(2026, 3, 7, 12, 0, tzinfo=UTC)
_CONSUMER_ID = UUID("12345678-1234-5678-1234-567812345678")
_API_KEY = "12345678.api-key-1"


def _poll_input() -> PollOperationInput:
    return PollOperationInput(
        blz=BankLeitzahl("12345678"),
        user_id="user-1",
        password="pass-1",
    )


def _session(
    *,
    operation_id: str = "op-1",
    status: OperationStatus = OperationStatus.PENDING_CONFIRMATION,
    session_state: bytes | None = b"snapshot-bytes",
) -> PendingOperationSession:
    return PendingOperationSession(
        operation_id=operation_id,
        consumer_id=_CONSUMER_ID,
        protocol=BankProtocol.FINTS,
        operation_type=OperationType.ACCOUNTS,
        session_state=session_state,
        status=status,
        created_at=_NOW,
        expires_at=_NOW + timedelta(minutes=5),
    )


def _build_use_case(
    *,
    sessions=None,
    resume_results=None,
    has_institute: bool = True,
):
    consumer = ApiConsumer(
        consumer_id=_CONSUMER_ID,
        email="test@example.com",
        api_key_hash=ApiKeyHash("12345678.api-key-1"),
        status=ConsumerStatus.ACTIVE,
        created_at=_NOW,
    )
    session_store = FakeOperationSessionStore(sessions or [])
    connector = FakeBankingConnector(resume_results=resume_results or [])
    # institute_cache = FakeConsumerCache()

    # Reuse the FakeConsumerCache pattern for institute catalog
    from tests.apps.gateway.fakes import FakeInstituteCache

    institute = None
    if has_institute:
        from datetime import date

        from gateway.domain.banking_gateway import FinTSInstitute

        institute = FinTSInstitute(
            blz=BankLeitzahl("12345678"),
            bic="GENODEF1ABC",
            name="Example Bank",
            city="Berlin",
            organization="Example Org",
            pin_tan_url="https://bank.example/fints",
            fints_version="3.0",
            last_source_update=date(2026, 3, 7),
        )

    institute_catalog = FakeInstituteCache(institutes=[institute] if institute else [])

    authenticate = AuthenticateConsumerQuery(
        consumer_cache=FakeConsumerCache(consumers=[consumer]),
        api_key_verifier=StubApiKeyVerifier(),
    )

    command = PollOperationCommand(
        authenticate_consumer=authenticate,
        institute_catalog=institute_catalog,
        connector=connector,
        session_store=session_store,
        id_provider=FakeIdProvider(now_value=_NOW, operation_ids=[]),
        ttl_seconds=120,
    )
    return command, session_store


def test_poll_returns_expired_when_session_not_found() -> None:
    command, _ = _build_use_case()
    result = asyncio.run(command("nonexistent", _poll_input(), _API_KEY))

    assert result.status == OperationStatus.EXPIRED


def test_poll_returns_expired_when_consumer_mismatch() -> None:
    session = _session()
    other_consumer_session = session.model_copy(
        update={"consumer_id": UUID("99999999-9999-9999-9999-999999999999")}
    )
    command, _ = _build_use_case(sessions=[other_consumer_session])
    result = asyncio.run(command("op-1", _poll_input(), _API_KEY))

    assert result.status == OperationStatus.EXPIRED


def test_poll_returns_current_status_when_not_pending() -> None:
    session = PendingOperationSession(
        operation_id="op-1",
        consumer_id=_CONSUMER_ID,
        protocol=BankProtocol.FINTS,
        operation_type=OperationType.ACCOUNTS,
        session_state=None,
        status=OperationStatus.COMPLETED,
        created_at=_NOW,
        expires_at=_NOW + timedelta(minutes=5),
        result_payload={"accounts": []},
    )
    command, _ = _build_use_case(sessions=[session])
    result = asyncio.run(command("op-1", _poll_input(), _API_KEY))

    assert result.status == OperationStatus.COMPLETED
    assert result.result_payload == {"accounts": []}


def test_poll_returns_pending_when_resume_still_pending() -> None:
    command, store = _build_use_case(
        sessions=[_session()],
        resume_results=[
            ResumeResult(
                status=OperationStatus.PENDING_CONFIRMATION,
                session_state=b"updated-snapshot",
                expires_at=_NOW + timedelta(minutes=4),
            )
        ],
    )
    result = asyncio.run(command("op-1", _poll_input(), _API_KEY))

    assert result.status == OperationStatus.PENDING_CONFIRMATION
    updated = asyncio.run(store.get("op-1"))
    assert updated.session_state == b"updated-snapshot"
    assert updated.last_polled_at == _NOW


def test_poll_returns_completed_on_approval() -> None:
    command, store = _build_use_case(
        sessions=[_session()],
        resume_results=[
            ResumeResult(
                status=OperationStatus.COMPLETED,
                result_payload={"accounts": [{"id": "acc-1"}]},
            )
        ],
    )
    result = asyncio.run(command("op-1", _poll_input(), _API_KEY))

    assert result.status == OperationStatus.COMPLETED
    assert result.result_payload == {"accounts": [{"id": "acc-1"}]}
    stored = asyncio.run(store.get("op-1"))
    assert stored.status is OperationStatus.COMPLETED
    assert stored.session_state is None


def test_poll_returns_failed_on_error() -> None:
    command, store = _build_use_case(
        sessions=[_session()],
        resume_results=[
            ResumeResult(
                status=OperationStatus.FAILED,
                failure_reason="TAN timed out",
            )
        ],
    )
    result = asyncio.run(command("op-1", _poll_input(), _API_KEY))

    assert result.status == OperationStatus.FAILED
    assert result.failure_reason == "TAN timed out"
    stored = asyncio.run(store.get("op-1"))
    assert stored.status is OperationStatus.FAILED


def test_poll_raises_when_institute_not_found() -> None:
    command, _ = _build_use_case(
        sessions=[_session()],
        has_institute=False,
    )
    with pytest.raises(InstitutionNotFoundError):
        asyncio.run(command("op-1", _poll_input(), _API_KEY))
