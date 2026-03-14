"""Tests for the ListAccounts use case."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from gateway.application.auth.queries.authenticate_consumer import (
    AuthenticateConsumerQuery,
)
from gateway.application.banking.commands.list_accounts import (
    ListAccountsCommand,
    ListAccountsInput,
)
from gateway.application.common import InstitutionNotFoundError, InternalError
from gateway.domain.banking_gateway import AccountsResult, OperationStatus
from gateway.domain.consumer_access import (
    ApiConsumer,
    ApiKeyHash,
    ConsumerId,
    ConsumerStatus,
    EmailAddress,
)
from gateway.domain.institution_catalog import (
    BankLeitzahl,
    Bic,
    FinTSInstitute,
    InstituteEndpoint,
)
from gateway.domain.shared import BankProtocol
from tests.apps.gateway.fakes import (
    FakeBankingConnector,
    FakeConsumerCache,
    FakeIdProvider,
    FakeInstituteCache,
    FakeOperationSessionStore,
    FakeProductKeyProvider,
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

    result = asyncio.run(use_case(_request(), presented_api_key="api-key-1"))

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

    result = asyncio.run(use_case(_request(), presented_api_key="api-key-1"))
    stored_session = asyncio.run(session_store.get("op-123"))

    assert result.status is OperationStatus.PENDING_CONFIRMATION
    assert result.operation_id == "op-123"
    assert result.expires_at == now + timedelta(minutes=5)
    assert stored_session is not None
    assert stored_session.operation_id == "op-123"
    assert stored_session.operation_type == "accounts"


def test_list_accounts_raises_for_unknown_institute() -> None:
    use_case, _, _ = _build_use_case(
        institute_cache=FakeInstituteCache(),
        connector=FakeBankingConnector(
            accounts_results=[AccountsResult(status=OperationStatus.COMPLETED)]
        ),
    )

    with pytest.raises(InstitutionNotFoundError, match="No institute found"):
        asyncio.run(use_case(_request(), presented_api_key="api-key-1"))


def test_list_accounts_raises_when_product_key_is_missing() -> None:
    use_case, _, _ = _build_use_case(
        product_key_provider=FakeProductKeyProvider(),
        connector=FakeBankingConnector(
            accounts_results=[AccountsResult(status=OperationStatus.COMPLETED)]
        ),
    )

    with pytest.raises(InternalError, match="No current product key is loaded"):
        asyncio.run(use_case(_request(), presented_api_key="api-key-1"))


def _build_use_case(
    *,
    institute_cache: FakeInstituteCache | None = None,
    product_key_provider: FakeProductKeyProvider | None = None,
    connector: FakeBankingConnector | None = None,
    session_store: FakeOperationSessionStore | None = None,
    id_provider: FakeIdProvider | None = None,
) -> tuple[ListAccountsCommand, FakeOperationSessionStore, FakeBankingConnector]:
    consumer = ApiConsumer(
        consumer_id=ConsumerId(UUID("12345678-1234-5678-1234-567812345678")),
        email=EmailAddress("consumer@example.com"),
        api_key_hash=ApiKeyHash("api-key-1"),
        status=ConsumerStatus.ACTIVE,
        created_at=datetime.now(UTC),
    )
    authenticate_consumer = AuthenticateConsumerQuery(
        FakeConsumerCache([consumer]), StubApiKeyVerifier()
    )
    resolved_institute_cache = institute_cache or FakeInstituteCache([_institute()])
    resolved_product_key_provider = product_key_provider or FakeProductKeyProvider(
        "product-key-1"
    )
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
            current_product_key_provider=resolved_product_key_provider,
            connector=resolved_connector,
            session_store=resolved_session_store,
            id_provider=resolved_id_provider,
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
        bic=Bic("GENODEF1ABC"),
        name="Example Bank",
        city="Berlin",
        organization="Example Org",
        pin_tan_url=InstituteEndpoint("https://bank.example/fints"),
        fints_version="3.0",
        last_source_update=datetime(2026, 3, 7, tzinfo=UTC).date(),
        source_row_checksum="checksum-1",
        source_payload={"row": 1},
    )
