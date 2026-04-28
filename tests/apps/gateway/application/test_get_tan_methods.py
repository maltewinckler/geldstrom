"""Tests for the GetAllowedTanMethods use case."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from gateway.application.banking.commands.get_tan_methods import (
    GetTanMethodsCommand,
    GetTanMethodsInput,
)
from gateway.application.consumer.queries.authenticate_consumer import (
    AuthenticateConsumerQuery,
)
from gateway.domain.banking_gateway import (
    BankLeitzahl,
    BankProtocol,
    FinTSInstitute,
    OperationStatus,
    TanMethod,
    TanMethodsResult,
)
from gateway.domain.consumer_access import (
    ApiConsumer,
    ApiKeyHash,
    ConsumerStatus,
)
from tests.apps.gateway.fakes import (
    FakeAuditService,
    FakeBankingConnector,
    FakeConsumerRepository,
    FakeIdProvider,
    FakeInstituteCache,
    FakeOperationSessionStore,
)


class StubApiKeyVerifier:
    def verify(self, presented_key: str, stored_hash: ApiKeyHash) -> bool:
        return presented_key == stored_hash.value


def test_get_tan_methods_filters_to_decoupled_methods() -> None:
    use_case, _, connector = _build_use_case(
        connector=FakeBankingConnector(
            tan_methods_results=[
                TanMethodsResult(
                    status=OperationStatus.COMPLETED,
                    methods=[
                        TanMethod(
                            method_id="942",
                            display_name="App-Freigabe",
                            is_decoupled=True,
                        ),
                        TanMethod(
                            method_id="999",
                            display_name="smsTAN",
                            is_decoupled=False,
                        ),
                    ],
                )
            ]
        )
    )

    result = asyncio.run(use_case(_request(), presented_api_key="12345678.api-key-1"))

    assert result.status is OperationStatus.COMPLETED
    assert result.methods == [
        TanMethod(method_id="942", display_name="App-Freigabe", is_decoupled=True)
    ]
    operation_name, payload = connector.calls[0]
    assert operation_name == "get_tan_methods"
    assert payload["institute"].blz == BankLeitzahl("12345678")


def test_get_tan_methods_creates_pending_session_for_decoupled_flow() -> None:
    now = datetime(2026, 3, 7, 12, 0, tzinfo=UTC)
    session_store = FakeOperationSessionStore()
    use_case, resolved_session_store, _ = _build_use_case(
        connector=FakeBankingConnector(
            tan_methods_results=[
                TanMethodsResult(
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
    assert stored_session.operation_type == "tan_methods"


def test_get_tan_methods_session_expires_at_is_capped_by_gateway_ttl() -> None:
    now = datetime(2026, 3, 7, 12, 0, tzinfo=UTC)
    session_store = FakeOperationSessionStore()
    use_case, _, _ = _build_use_case(
        connector=FakeBankingConnector(
            tan_methods_results=[
                TanMethodsResult(
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


def _build_use_case(
    *,
    institute_cache: FakeInstituteCache | None = None,
    connector: FakeBankingConnector | None = None,
    session_store: FakeOperationSessionStore | None = None,
    id_provider: FakeIdProvider | None = None,
    ttl_seconds: int = 600,
) -> tuple[GetTanMethodsCommand, FakeOperationSessionStore, FakeBankingConnector]:
    from unittest.mock import AsyncMock

    consumer = ApiConsumer(
        consumer_id=UUID("12345678-1234-5678-1234-567812345678"),
        email="consumer@example.com",
        api_key_hash=ApiKeyHash("12345678.api-key-1"),
        status=ConsumerStatus.ACTIVE,
        created_at=datetime.now(UTC),
    )
    authenticate_consumer = AuthenticateConsumerQuery(
        FakeConsumerRepository([consumer]), StubApiKeyVerifier(), FakeAuditService()
    )
    resolved_institute_cache = institute_cache or FakeInstituteCache([_institute()])
    resolved_connector = connector or FakeBankingConnector(
        tan_methods_results=[TanMethodsResult(status=OperationStatus.COMPLETED)]
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
        GetTanMethodsCommand(
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


def _request() -> GetTanMethodsInput:
    return GetTanMethodsInput(
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
