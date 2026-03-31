"""Tests for the GetOperationStatus use case."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from gateway.application.banking.queries.get_operation_status import (
    GetOperationStatusQuery,
)
from gateway.application.common import ForbiddenError, OperationNotFoundError
from gateway.application.consumer.queries.authenticate_consumer import (
    AuthenticateConsumerQuery,
)
from gateway.domain.banking_gateway import (
    BankProtocol,
    OperationStatus,
    OperationType,
    PendingOperationSession,
)
from gateway.domain.consumer_access import (
    ApiConsumer,
    ApiKeyHash,
    ConsumerStatus,
)
from tests.apps.gateway.fakes import (
    FakeConsumerCache,
    FakeIdProvider,
    FakeOperationSessionStore,
)


class StubApiKeyVerifier:
    def verify(self, presented_key: str, stored_hash: ApiKeyHash) -> bool:
        return presented_key == stored_hash.value


def test_get_operation_status_returns_failed_session_without_deleting() -> None:
    use_case, session_store = _build_use_case(
        sessions=[
            _session(
                operation_id="op-1",
                status=OperationStatus.FAILED,
                failure_reason="bank rejected",
            )
        ]
    )

    result = asyncio.run(use_case("op-1", presented_api_key="12345678.api-key-1"))
    stored_session = asyncio.run(session_store.get("op-1"))

    assert result.status is OperationStatus.FAILED
    assert result.failure_reason == "bank rejected"
    assert stored_session is not None


def test_get_operation_status_returns_expired_session_without_deleting() -> None:
    """Sessions marked EXPIRED by the resume worker persist until expire_stale."""
    use_case, session_store = _build_use_case(
        sessions=[
            _session(
                operation_id="op-1",
                status=OperationStatus.EXPIRED,
            )
        ]
    )

    result = asyncio.run(use_case("op-1", presented_api_key="12345678.api-key-1"))
    stored_session = asyncio.run(session_store.get("op-1"))

    assert result.status is OperationStatus.EXPIRED
    assert stored_session is not None


def test_get_operation_status_rejects_access_from_other_consumer() -> None:
    use_case, _ = _build_use_case(
        sessions=[
            _session(
                operation_id="op-1",
                consumer_id="87654321-4321-8765-4321-876543218765",
                status=OperationStatus.PENDING_CONFIRMATION,
            )
        ]
    )

    with pytest.raises(ForbiddenError, match="does not belong"):
        asyncio.run(use_case("op-1", presented_api_key="12345678.api-key-1"))


def test_get_operation_status_returns_completed_result_without_deleting() -> None:
    use_case, session_store = _build_use_case(
        sessions=[
            _session(
                operation_id="op-1",
                status=OperationStatus.COMPLETED,
                result_payload={"accounts": [{"iban": "DE89370400440532013000"}]},
            )
        ]
    )

    result = asyncio.run(use_case("op-1", presented_api_key="12345678.api-key-1"))
    stored_session = asyncio.run(session_store.get("op-1"))

    assert result.status is OperationStatus.COMPLETED
    assert result.result_payload == {"accounts": [{"iban": "DE89370400440532013000"}]}
    assert stored_session is not None


def test_get_operation_status_raises_for_missing_operation() -> None:
    use_case, _ = _build_use_case()

    with pytest.raises(OperationNotFoundError, match="No operation found"):
        asyncio.run(use_case("missing-op", presented_api_key="12345678.api-key-1"))


def _build_use_case(
    *,
    sessions: list[PendingOperationSession] | None = None,
    consumers: list[ApiConsumer] | None = None,
    id_provider: FakeIdProvider | None = None,
) -> tuple[GetOperationStatusQuery, FakeOperationSessionStore]:
    resolved_consumers = consumers or [_consumer()]
    authenticate_consumer = AuthenticateConsumerQuery(
        FakeConsumerCache(resolved_consumers), StubApiKeyVerifier()
    )
    session_store = FakeOperationSessionStore(sessions)
    resolved_id_provider = id_provider or FakeIdProvider(
        now_value=datetime(2026, 3, 7, 12, 0, tzinfo=UTC),
        operation_ids=["op-unused"],
    )
    return (
        GetOperationStatusQuery(
            authenticate_consumer=authenticate_consumer,
            session_store=session_store,
            id_provider=resolved_id_provider,
        ),
        session_store,
    )


def _consumer(
    *,
    consumer_id: str = "12345678-1234-5678-1234-567812345678",
    email: str = "consumer@example.com",
    api_key_hash: str = "12345678.api-key-1",
) -> ApiConsumer:
    return ApiConsumer(
        consumer_id=UUID(consumer_id),
        email=email,
        api_key_hash=ApiKeyHash(api_key_hash),
        status=ConsumerStatus.ACTIVE,
        created_at=datetime.now(UTC),
    )


def _session(
    *,
    operation_id: str,
    consumer_id: str = "12345678-1234-5678-1234-567812345678",
    status: OperationStatus,
    result_payload: dict | None = None,
    failure_reason: str | None = None,
) -> PendingOperationSession:
    now = datetime(2026, 3, 7, 12, 0, tzinfo=UTC)
    is_pending = status is OperationStatus.PENDING_CONFIRMATION
    return PendingOperationSession(
        operation_id=operation_id,
        consumer_id=UUID(consumer_id),
        protocol=BankProtocol.FINTS,
        operation_type=OperationType.ACCOUNTS,
        session_state=b"opaque-state" if is_pending else None,
        status=status,
        created_at=now,
        expires_at=now + timedelta(minutes=5),
        result_payload=result_payload,
        failure_reason=failure_reason,
    )
