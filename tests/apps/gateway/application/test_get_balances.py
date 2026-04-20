"""Tests for the GetBalances use case."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from gateway.application.banking.commands.get_balances import (
    GetBalancesCommand,
    GetBalancesInput,
)
from gateway.application.common import InstitutionNotFoundError
from gateway.application.consumer.queries.authenticate_consumer import (
    AuthenticateConsumerQuery,
)
from gateway.domain.banking_gateway import (
    BalancesResult,
    BankLeitzahl,
    BankProtocol,
    FinTSInstitute,
    OperationStatus,
)
from gateway.domain.consumer_access import (
    ApiConsumer,
    ApiKeyHash,
    ConsumerStatus,
)
from tests.apps.gateway.fakes import (
    FakeAuditService,
    FakeBankingConnector,
    FakeConsumerCache,
    FakeIdProvider,
    FakeInstituteCache,
    FakeOperationSessionStore,
)

_BALANCE_ENTRY = {
    "account_id": "acc-1",
    "as_of": "2026-03-20T12:00:00+00:00",
    "booked_amount": "1234.56",
    "booked_currency": "EUR",
    "pending_amount": None,
    "pending_currency": None,
    "available_amount": None,
    "available_currency": None,
}


class StubApiKeyVerifier:
    def verify(self, presented_key: str, stored_hash: ApiKeyHash) -> bool:
        return presented_key == stored_hash.value


def test_get_balances_returns_completed_response() -> None:
    use_case, _, connector = _build_use_case(
        connector=FakeBankingConnector(
            balances_results=[
                BalancesResult(
                    status=OperationStatus.COMPLETED,
                    balances=[_BALANCE_ENTRY],
                )
            ]
        )
    )

    result = asyncio.run(use_case(_request(), presented_api_key="12345678.api-key-1"))

    assert result.status is OperationStatus.COMPLETED
    assert result.balances == [_BALANCE_ENTRY]
    assert result.operation_id is None
    operation_name, payload = connector.calls[0]
    assert operation_name == "get_balances"
    assert payload["institute"].blz == BankLeitzahl("12345678")


def test_get_balances_creates_pending_session_for_decoupled_flow() -> None:
    now = datetime(2026, 3, 7, 12, 0, tzinfo=UTC)
    session_store = FakeOperationSessionStore()
    use_case, _, _ = _build_use_case(
        connector=FakeBankingConnector(
            balances_results=[
                BalancesResult(
                    status=OperationStatus.PENDING_CONFIRMATION,
                    session_state=b"opaque-state",
                    expires_at=now + timedelta(minutes=5),
                )
            ]
        ),
        session_store=session_store,
        id_provider=FakeIdProvider(now_value=now, operation_ids=["op-789"]),
    )

    result = asyncio.run(use_case(_request(), presented_api_key="12345678.api-key-1"))
    stored_session = asyncio.run(session_store.get("op-789"))

    assert result.status is OperationStatus.PENDING_CONFIRMATION
    assert result.operation_id == "op-789"
    assert result.expires_at == now + timedelta(minutes=5)
    assert stored_session is not None
    assert stored_session.operation_id == "op-789"
    assert stored_session.operation_type == "balances"


def test_get_balances_session_expires_at_is_capped_by_gateway_ttl() -> None:
    now = datetime(2026, 3, 7, 12, 0, tzinfo=UTC)
    session_store = FakeOperationSessionStore()
    use_case, _, _ = _build_use_case(
        connector=FakeBankingConnector(
            balances_results=[
                BalancesResult(
                    status=OperationStatus.PENDING_CONFIRMATION,
                    session_state=b"state",
                    expires_at=now + timedelta(minutes=10),
                )
            ]
        ),
        session_store=session_store,
        id_provider=FakeIdProvider(now_value=now, operation_ids=["op-ttl"]),
        ttl_seconds=120,
    )

    result = asyncio.run(use_case(_request(), presented_api_key="12345678.api-key-1"))
    stored_session = asyncio.run(session_store.get("op-ttl"))

    assert result.expires_at == now + timedelta(seconds=120)
    assert stored_session is not None
    assert stored_session.expires_at == now + timedelta(seconds=120)


def test_get_balances_raises_for_unknown_institute() -> None:
    use_case, _, _ = _build_use_case(
        institute_cache=FakeInstituteCache(),
        connector=FakeBankingConnector(
            balances_results=[BalancesResult(status=OperationStatus.COMPLETED)]
        ),
    )

    with pytest.raises(InstitutionNotFoundError, match="No institute found"):
        asyncio.run(use_case(_request(), presented_api_key="12345678.api-key-1"))


def test_get_balances_returns_empty_list_when_no_balances() -> None:
    use_case, _, _ = _build_use_case(
        connector=FakeBankingConnector(
            balances_results=[
                BalancesResult(
                    status=OperationStatus.COMPLETED,
                    balances=[],
                )
            ]
        )
    )

    result = asyncio.run(use_case(_request(), presented_api_key="12345678.api-key-1"))

    assert result.status is OperationStatus.COMPLETED
    assert result.balances == []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_use_case(
    *,
    institute_cache: FakeInstituteCache | None = None,
    connector: FakeBankingConnector | None = None,
    session_store: FakeOperationSessionStore | None = None,
    id_provider: FakeIdProvider | None = None,
    ttl_seconds: int = 600,
) -> tuple[GetBalancesCommand, FakeOperationSessionStore, FakeBankingConnector]:
    from unittest.mock import AsyncMock

    consumer = ApiConsumer(
        consumer_id=UUID("12345678-1234-5678-1234-567812345678"),
        email="consumer@example.com",
        api_key_hash=ApiKeyHash("12345678.api-key-1"),
        status=ConsumerStatus.ACTIVE,
        created_at=datetime.now(UTC),
    )
    authenticate_consumer = AuthenticateConsumerQuery(
        FakeConsumerCache([consumer]), StubApiKeyVerifier(), FakeAuditService()
    )
    resolved_institute_cache = institute_cache or FakeInstituteCache([_institute()])
    resolved_connector = connector or FakeBankingConnector(
        balances_results=[BalancesResult(status=OperationStatus.COMPLETED)]
    )
    resolved_session_store = session_store or FakeOperationSessionStore()
    resolved_id_provider = id_provider or FakeIdProvider(
        now_value=datetime(2026, 3, 7, 12, 0, tzinfo=UTC),
        operation_ids=["op-1"],
    )
    factory = AsyncMock()
    factory.get_banking_connector = AsyncMock(return_value=resolved_connector)
    factory.caches.institute = resolved_institute_cache
    factory.caches.session_store = resolved_session_store
    factory.id_provider = resolved_id_provider
    factory.operation_session_ttl_seconds = ttl_seconds
    return (
        GetBalancesCommand(
            authenticate_consumer=authenticate_consumer,
            institute_catalog=resolved_institute_cache,
            factory=factory,
            session_store=resolved_session_store,
            id_provider=resolved_id_provider,
            ttl_seconds=ttl_seconds,
        ),
        resolved_session_store,
        resolved_connector,
    )


def _request() -> GetBalancesInput:
    return GetBalancesInput(
        protocol=BankProtocol.FINTS,
        blz=BankLeitzahl("12345678"),
        user_id="bank-user",
        password="bank-password",
    )


def _institute() -> FinTSInstitute:
    return FinTSInstitute(
        blz=BankLeitzahl("12345678"),
        bic="GENODEF1ABC",
        name="Example Bank",
        city="Berlin",
        organization="Example Org",
        pin_tan_url="https://bank.example/fints",
        fints_version="3.0",
        last_source_update=datetime(2026, 3, 7, tzinfo=UTC).date(),
    )
