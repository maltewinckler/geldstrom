"""Tests for the FetchHistoricalTransactions use case."""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

import pytest

from gateway.application.banking.commands.fetch_transactions import (
    FetchTransactionsCommand,
    FetchTransactionsInput,
)
from gateway.application.common import ValidationError
from gateway.application.consumer.queries.authenticate_consumer import (
    AuthenticateConsumerQuery,
)
from gateway.domain.banking_gateway import (
    BankLeitzahl,
    BankProtocol,
    FinTSInstitute,
    OperationStatus,
    TransactionsResult,
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


class StubApiKeyVerifier:
    def verify(self, presented_key: str, stored_hash: ApiKeyHash) -> bool:
        return presented_key == stored_hash.value


def test_fetch_transactions_uses_explicit_date_range() -> None:
    connector = FakeBankingConnector(
        transactions_results=[
            TransactionsResult(
                status=OperationStatus.COMPLETED,
                transactions=[{"transaction_id": "txn-1"}],
            )
        ]
    )
    use_case, _, resolved_connector, _ = _build_use_case(connector=connector)

    result = asyncio.run(
        use_case(
            _request(start_date=date(2026, 1, 1), end_date=date(2026, 2, 1)),
            presented_api_key="12345678.api-key-1",
        )
    )

    assert result.status is OperationStatus.COMPLETED
    assert result.transactions == [{"transaction_id": "txn-1"}]
    operation_name, payload = resolved_connector.calls[0]
    assert operation_name == "fetch_transactions"
    assert payload["institute"].blz == BankLeitzahl("12345678")
    assert payload["start_date"] == date(2026, 1, 1)
    assert payload["end_date"] == date(2026, 2, 1)


def test_fetch_transactions_defaults_to_last_ninety_days() -> None:
    now = datetime(2026, 3, 7, 12, 0, tzinfo=UTC)
    connector = FakeBankingConnector(
        transactions_results=[
            TransactionsResult(
                status=OperationStatus.COMPLETED,
                transactions=[{"transaction_id": "txn-1"}],
            )
        ]
    )
    use_case, _, resolved_connector, _ = _build_use_case(
        connector=connector,
        id_provider=FakeIdProvider(now_value=now, operation_ids=["op-1"]),
    )

    result = asyncio.run(use_case(_request(), presented_api_key="12345678.api-key-1"))

    assert result.status is OperationStatus.COMPLETED
    operation_name, payload = resolved_connector.calls[0]
    assert operation_name == "fetch_transactions"
    assert payload["institute"].blz == BankLeitzahl("12345678")
    assert payload["start_date"] == date(2025, 12, 7)
    assert payload["end_date"] == date(2026, 3, 7)


def test_fetch_transactions_creates_pending_session_for_decoupled_flow() -> None:
    now = datetime(2026, 3, 7, 12, 0, tzinfo=UTC)
    session_store = FakeOperationSessionStore()
    use_case, resolved_session_store, _, _ = _build_use_case(
        connector=FakeBankingConnector(
            transactions_results=[
                TransactionsResult(
                    status=OperationStatus.PENDING_CONFIRMATION,
                    session_state=b"opaque-state",
                    expires_at=now + timedelta(minutes=5),
                )
            ]
        ),
        session_store=session_store,
        id_provider=FakeIdProvider(now_value=now, operation_ids=["op-123"]),
    )

    result = asyncio.run(use_case(_request(), presented_api_key="12345678.api-key-1"))
    stored_session = asyncio.run(resolved_session_store.get("op-123"))

    assert result.status is OperationStatus.PENDING_CONFIRMATION
    assert result.operation_id == "op-123"
    assert result.expires_at == now + timedelta(minutes=5)
    assert stored_session is not None
    assert stored_session.operation_id == "op-123"
    assert stored_session.operation_type == "transactions"


def test_fetch_transactions_session_expires_at_is_capped_by_gateway_ttl() -> None:
    now = datetime(2026, 3, 7, 12, 0, tzinfo=UTC)
    session_store = FakeOperationSessionStore()
    use_case, resolved_session_store, _, _ = _build_use_case(
        connector=FakeBankingConnector(
            transactions_results=[
                TransactionsResult(
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
    stored_session = asyncio.run(resolved_session_store.get("op-ttl"))

    assert result.expires_at == now + timedelta(seconds=120)
    assert stored_session is not None
    assert stored_session.expires_at == now + timedelta(seconds=120)


def test_fetch_transactions_rejects_inverted_date_range() -> None:
    use_case, _, resolved_connector, _ = _build_use_case()

    with pytest.raises(
        ValidationError, match="start_date must be on or before end_date"
    ):
        asyncio.run(
            use_case(
                _request(
                    start_date=date(2026, 2, 1),
                    end_date=date(2026, 1, 1),
                ),
                presented_api_key="12345678.api-key-1",
            )
        )

    assert resolved_connector.calls == []


def test_fetch_transactions_rejects_range_exceeding_365_days() -> None:
    use_case, _, resolved_connector, _ = _build_use_case()

    with pytest.raises(ValidationError, match="Date range must not exceed 365 days"):
        asyncio.run(
            use_case(
                _request(
                    start_date=date(2025, 1, 1),
                    end_date=date(2026, 3, 7),
                ),
                presented_api_key="12345678.api-key-1",
            )
        )

    assert resolved_connector.calls == []


def _build_use_case(
    *,
    institute_cache: FakeInstituteCache | None = None,
    connector: FakeBankingConnector | None = None,
    session_store: FakeOperationSessionStore | None = None,
    id_provider: FakeIdProvider | None = None,
    ttl_seconds: int = 600,
) -> tuple[
    FetchTransactionsCommand,
    FakeOperationSessionStore,
    FakeBankingConnector,
    FakeIdProvider,
]:
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
        transactions_results=[TransactionsResult(status=OperationStatus.COMPLETED)]
    )
    resolved_session_store = session_store or FakeOperationSessionStore()
    resolved_id_provider = id_provider or FakeIdProvider(
        now_value=datetime(2026, 3, 7, 12, 0, tzinfo=UTC),
        operation_ids=["op-1"],
    )
    return (
        FetchTransactionsCommand(
            authenticate_consumer=authenticate_consumer,
            institute_catalog=resolved_institute_cache,
            connector=resolved_connector,
            session_store=resolved_session_store,
            id_provider=resolved_id_provider,
            ttl_seconds=ttl_seconds,
        ),
        resolved_session_store,
        resolved_connector,
        resolved_id_provider,
    )


def _request(
    *, start_date: date | None = None, end_date: date | None = None
) -> FetchTransactionsInput:
    return FetchTransactionsInput(
        protocol=BankProtocol.FINTS,
        blz=BankLeitzahl("12345678"),
        user_id="bank-user",
        password="bank-password",
        iban="DE89370400440532013000",
        start_date=start_date,
        end_date=end_date,
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
