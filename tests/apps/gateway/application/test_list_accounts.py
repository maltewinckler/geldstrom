"""Tests for the ListAccounts use case."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from gateway.application.banking.commands.list_accounts import (
    ListAccountsCommand,
    ListAccountsInput,
)
from gateway.application.common import InstitutionNotFoundError
from gateway.application.consumer.queries.authenticate_consumer import (
    AuthenticateConsumerQuery,
)
from gateway.domain.banking_gateway import (
    AccountsResult,
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


class StubApiKeyVerifier:
    def verify(self, presented_key: str, stored_hash: ApiKeyHash) -> bool:
        return presented_key == stored_hash.value


def test_list_accounts_returns_completed_response() -> None:
    use_case, _, connector = _build_use_case(
        connector=FakeBankingConnector(
            accounts_results=[
                AccountsResult(
                    status=OperationStatus.COMPLETED,
                    accounts=[{"iban": "DE89370400440532013000"}],
                )
            ]
        )
    )

    result = asyncio.run(use_case(_request(), presented_api_key="12345678.api-key-1"))

    assert result.status is OperationStatus.COMPLETED
    assert result.accounts == [{"iban": "DE89370400440532013000"}]
    assert result.operation_id is None
    operation_name, payload = connector.calls[0]
    assert operation_name == "list_accounts"
    assert payload["institute"].blz == BankLeitzahl("12345678")


def test_list_accounts_creates_pending_session_for_decoupled_flow() -> None:
    now = datetime(2026, 3, 7, 12, 0, tzinfo=UTC)
    session_store = FakeOperationSessionStore()
    use_case, _, _ = _build_use_case(
        connector=FakeBankingConnector(
            accounts_results=[
                AccountsResult(
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
    stored_session = asyncio.run(session_store.get("op-123"))

    assert result.status is OperationStatus.PENDING_CONFIRMATION
    assert result.operation_id == "op-123"
    assert result.expires_at == now + timedelta(minutes=5)
    assert stored_session is not None
    assert stored_session.operation_id == "op-123"
    assert stored_session.operation_type == "accounts"


def test_list_accounts_session_expires_at_is_capped_by_gateway_ttl() -> None:
    now = datetime(2026, 3, 7, 12, 0, tzinfo=UTC)
    session_store = FakeOperationSessionStore()
    use_case, _, _ = _build_use_case(
        connector=FakeBankingConnector(
            accounts_results=[
                AccountsResult(
                    status=OperationStatus.PENDING_CONFIRMATION,
                    session_state=b"state",
                    expires_at=now + timedelta(minutes=10),  # bank allows 10 min
                )
            ]
        ),
        session_store=session_store,
        id_provider=FakeIdProvider(now_value=now, operation_ids=["op-ttl"]),
        ttl_seconds=120,  # gateway caps at 2 min
    )

    result = asyncio.run(use_case(_request(), presented_api_key="12345678.api-key-1"))
    stored_session = asyncio.run(session_store.get("op-ttl"))

    assert result.expires_at == now + timedelta(seconds=120)
    assert stored_session is not None
    assert stored_session.expires_at == now + timedelta(seconds=120)


def test_list_accounts_session_uses_bank_expires_at_when_shorter_than_ttl() -> None:
    now = datetime(2026, 3, 7, 12, 0, tzinfo=UTC)
    session_store = FakeOperationSessionStore()
    use_case, _, _ = _build_use_case(
        connector=FakeBankingConnector(
            accounts_results=[
                AccountsResult(
                    status=OperationStatus.PENDING_CONFIRMATION,
                    session_state=b"state",
                    expires_at=now + timedelta(seconds=30),  # bank only allows 30 s
                )
            ]
        ),
        session_store=session_store,
        id_provider=FakeIdProvider(now_value=now, operation_ids=["op-short"]),
        ttl_seconds=120,
    )

    result = asyncio.run(use_case(_request(), presented_api_key="12345678.api-key-1"))
    stored_session = asyncio.run(session_store.get("op-short"))

    assert result.expires_at == now + timedelta(seconds=30)
    assert stored_session is not None
    assert stored_session.expires_at == now + timedelta(seconds=30)


def test_list_accounts_raises_for_unknown_institute() -> None:
    use_case, _, _ = _build_use_case(
        institute_cache=FakeInstituteCache(),
        connector=FakeBankingConnector(
            accounts_results=[AccountsResult(status=OperationStatus.COMPLETED)]
        ),
    )

    with pytest.raises(InstitutionNotFoundError, match="No institute found"):
        asyncio.run(use_case(_request(), presented_api_key="12345678.api-key-1"))


def _build_use_case(
    *,
    institute_cache: FakeInstituteCache | None = None,
    connector: FakeBankingConnector | None = None,
    session_store: FakeOperationSessionStore | None = None,
    id_provider: FakeIdProvider | None = None,
    ttl_seconds: int = 600,
) -> tuple[ListAccountsCommand, FakeOperationSessionStore, FakeBankingConnector]:
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
        accounts_results=[AccountsResult(status=OperationStatus.COMPLETED)]
    )
    resolved_session_store = session_store or FakeOperationSessionStore()
    resolved_id_provider = id_provider or FakeIdProvider(
        now_value=datetime(2026, 3, 7, 12, 0, tzinfo=UTC),
        operation_ids=["op-1"],
    )
    return (
        ListAccountsCommand(
            authenticate_consumer=authenticate_consumer,
            institute_catalog=resolved_institute_cache,
            connector=resolved_connector,
            session_store=resolved_session_store,
            id_provider=resolved_id_provider,
            ttl_seconds=ttl_seconds,
        ),
        resolved_session_store,
        resolved_connector,
    )


def _request() -> ListAccountsInput:
    return ListAccountsInput(
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
