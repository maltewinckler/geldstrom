"""Tests verifying each banking command calls factory.get_banking_connector()
and propagates GatewayMisconfiguredError correctly.

Validates: Requirements 6.2, 6.3
"""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from gateway.application.banking.commands.fetch_transactions import (
    FetchTransactionsCommand,
    FetchTransactionsInput,
)
from gateway.application.banking.commands.get_balances import (
    GetBalancesCommand,
    GetBalancesInput,
)
from gateway.application.banking.commands.get_tan_methods import (
    GetTanMethodsCommand,
    GetTanMethodsInput,
)
from gateway.application.banking.commands.list_accounts import (
    ListAccountsCommand,
    ListAccountsInput,
)
from gateway.application.banking.commands.poll_operation import (
    PollOperationCommand,
    PollOperationInput,
)
from gateway.application.common import GatewayMisconfiguredError
from gateway.application.consumer.queries.authenticate_consumer import (
    AuthenticateConsumerQuery,
)
from gateway.domain.banking_gateway import (
    AccountsResult,
    BalancesResult,
    BankLeitzahl,
    BankProtocol,
    FinTSInstitute,
    OperationStatus,
    OperationType,
    PendingOperationSession,
    TanMethodsResult,
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

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 3, 7, 12, 0, tzinfo=UTC)
_CONSUMER_ID = UUID("12345678-1234-5678-1234-567812345678")
_API_KEY = "12345678.api-key-1"


class _StubApiKeyVerifier:
    def verify(self, presented_key: str, stored_hash: ApiKeyHash) -> bool:
        return presented_key == stored_hash.value


def _consumer() -> ApiConsumer:
    return ApiConsumer(
        consumer_id=_CONSUMER_ID,
        email="consumer@example.com",
        api_key_hash=ApiKeyHash(_API_KEY),
        status=ConsumerStatus.ACTIVE,
        created_at=_NOW,
    )


def _authenticate_consumer() -> AuthenticateConsumerQuery:
    return AuthenticateConsumerQuery(
        FakeConsumerCache([_consumer()]),
        _StubApiKeyVerifier(),
        FakeAuditService(),
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
        last_source_update=date(2026, 3, 7),
    )


def _make_factory(connector: FakeBankingConnector) -> AsyncMock:
    """Return a mock factory whose get_banking_connector() returns *connector*."""
    factory = AsyncMock()
    factory.get_banking_connector = AsyncMock(return_value=connector)
    factory.caches.institute = FakeInstituteCache([_institute()])
    factory.caches.session_store = FakeOperationSessionStore()
    factory.id_provider = FakeIdProvider(now_value=_NOW, operation_ids=["op-1"])
    factory.operation_session_ttl_seconds = 600
    return factory


def _make_misconfigured_factory() -> AsyncMock:
    """Return a mock factory whose get_banking_connector() raises GatewayMisconfiguredError."""
    factory = AsyncMock()
    factory.get_banking_connector = AsyncMock(
        side_effect=GatewayMisconfiguredError(
            "gateway misconfigured: no product registration"
        )
    )
    factory.caches.institute = FakeInstituteCache([_institute()])
    factory.caches.session_store = FakeOperationSessionStore()
    factory.id_provider = FakeIdProvider(now_value=_NOW, operation_ids=["op-1"])
    factory.operation_session_ttl_seconds = 600
    return factory


# ---------------------------------------------------------------------------
# ListAccountsCommand
# ---------------------------------------------------------------------------


def test_list_accounts_calls_get_banking_connector() -> None:
    connector = FakeBankingConnector(
        accounts_results=[AccountsResult(status=OperationStatus.COMPLETED, accounts=[])]
    )
    factory = _make_factory(connector)
    command = ListAccountsCommand(
        authenticate_consumer=_authenticate_consumer(),
        institute_catalog=factory.caches.institute,
        factory=factory,
        session_store=factory.caches.session_store,
        id_provider=factory.id_provider,
    )

    asyncio.run(command(_list_accounts_request(), presented_api_key=_API_KEY))

    factory.get_banking_connector.assert_awaited_once()


def test_list_accounts_propagates_gateway_misconfigured_error() -> None:
    factory = _make_misconfigured_factory()
    command = ListAccountsCommand(
        authenticate_consumer=_authenticate_consumer(),
        institute_catalog=factory.caches.institute,
        factory=factory,
        session_store=factory.caches.session_store,
        id_provider=factory.id_provider,
    )

    with pytest.raises(GatewayMisconfiguredError):
        asyncio.run(command(_list_accounts_request(), presented_api_key=_API_KEY))


def _list_accounts_request() -> ListAccountsInput:
    return ListAccountsInput(
        protocol=BankProtocol.FINTS,
        blz=BankLeitzahl("12345678"),
        user_id="bank-user",
        password="bank-password",
    )


# ---------------------------------------------------------------------------
# FetchTransactionsCommand
# ---------------------------------------------------------------------------


def test_fetch_transactions_calls_get_banking_connector() -> None:
    connector = FakeBankingConnector(
        transactions_results=[
            TransactionsResult(status=OperationStatus.COMPLETED, transactions=[])
        ]
    )
    factory = _make_factory(connector)
    command = FetchTransactionsCommand(
        authenticate_consumer=_authenticate_consumer(),
        institute_catalog=factory.caches.institute,
        factory=factory,
        session_store=factory.caches.session_store,
        id_provider=factory.id_provider,
    )

    asyncio.run(command(_fetch_transactions_request(), presented_api_key=_API_KEY))

    factory.get_banking_connector.assert_awaited_once()


def test_fetch_transactions_propagates_gateway_misconfigured_error() -> None:
    factory = _make_misconfigured_factory()
    command = FetchTransactionsCommand(
        authenticate_consumer=_authenticate_consumer(),
        institute_catalog=factory.caches.institute,
        factory=factory,
        session_store=factory.caches.session_store,
        id_provider=factory.id_provider,
    )

    with pytest.raises(GatewayMisconfiguredError):
        asyncio.run(command(_fetch_transactions_request(), presented_api_key=_API_KEY))


def _fetch_transactions_request() -> FetchTransactionsInput:
    return FetchTransactionsInput(
        protocol=BankProtocol.FINTS,
        blz=BankLeitzahl("12345678"),
        user_id="bank-user",
        password="bank-password",
        iban="DE89370400440532013000",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 2, 1),
    )


# ---------------------------------------------------------------------------
# GetBalancesCommand
# ---------------------------------------------------------------------------


def test_get_balances_calls_get_banking_connector() -> None:
    connector = FakeBankingConnector(
        balances_results=[BalancesResult(status=OperationStatus.COMPLETED, balances=[])]
    )
    factory = _make_factory(connector)
    command = GetBalancesCommand(
        authenticate_consumer=_authenticate_consumer(),
        institute_catalog=factory.caches.institute,
        factory=factory,
        session_store=factory.caches.session_store,
        id_provider=factory.id_provider,
    )

    asyncio.run(command(_get_balances_request(), presented_api_key=_API_KEY))

    factory.get_banking_connector.assert_awaited_once()


def test_get_balances_propagates_gateway_misconfigured_error() -> None:
    factory = _make_misconfigured_factory()
    command = GetBalancesCommand(
        authenticate_consumer=_authenticate_consumer(),
        institute_catalog=factory.caches.institute,
        factory=factory,
        session_store=factory.caches.session_store,
        id_provider=factory.id_provider,
    )

    with pytest.raises(GatewayMisconfiguredError):
        asyncio.run(command(_get_balances_request(), presented_api_key=_API_KEY))


def _get_balances_request() -> GetBalancesInput:
    return GetBalancesInput(
        protocol=BankProtocol.FINTS,
        blz=BankLeitzahl("12345678"),
        user_id="bank-user",
        password="bank-password",
    )


# ---------------------------------------------------------------------------
# GetTanMethodsCommand
# ---------------------------------------------------------------------------


def test_get_tan_methods_calls_get_banking_connector() -> None:
    connector = FakeBankingConnector(
        tan_methods_results=[
            TanMethodsResult(status=OperationStatus.COMPLETED, methods=[])
        ]
    )
    factory = _make_factory(connector)
    command = GetTanMethodsCommand(
        authenticate_consumer=_authenticate_consumer(),
        institute_catalog=factory.caches.institute,
        factory=factory,
        session_store=factory.caches.session_store,
        id_provider=factory.id_provider,
    )

    asyncio.run(command(_get_tan_methods_request(), presented_api_key=_API_KEY))

    factory.get_banking_connector.assert_awaited_once()


def test_get_tan_methods_propagates_gateway_misconfigured_error() -> None:
    factory = _make_misconfigured_factory()
    command = GetTanMethodsCommand(
        authenticate_consumer=_authenticate_consumer(),
        institute_catalog=factory.caches.institute,
        factory=factory,
        session_store=factory.caches.session_store,
        id_provider=factory.id_provider,
    )

    with pytest.raises(GatewayMisconfiguredError):
        asyncio.run(command(_get_tan_methods_request(), presented_api_key=_API_KEY))


def _get_tan_methods_request() -> GetTanMethodsInput:
    return GetTanMethodsInput(
        protocol=BankProtocol.FINTS,
        blz=BankLeitzahl("12345678"),
        user_id="bank-user",
        password="bank-password",
    )


# ---------------------------------------------------------------------------
# PollOperationCommand
# ---------------------------------------------------------------------------


def _pending_session() -> PendingOperationSession:
    return PendingOperationSession(
        operation_id="op-1",
        consumer_id=_CONSUMER_ID,
        protocol=BankProtocol.FINTS,
        operation_type=OperationType.ACCOUNTS,
        session_state=b"snapshot",
        status=OperationStatus.PENDING_CONFIRMATION,
        created_at=_NOW,
        expires_at=_NOW + timedelta(minutes=5),
    )


def test_poll_operation_calls_get_banking_connector() -> None:
    from gateway.domain.banking_gateway import ResumeResult

    connector = FakeBankingConnector(
        resume_results=[
            ResumeResult(
                status=OperationStatus.COMPLETED,
                result_payload={"accounts": []},
            )
        ]
    )
    session_store = FakeOperationSessionStore([_pending_session()])
    factory = AsyncMock()
    factory.get_banking_connector = AsyncMock(return_value=connector)
    factory.caches.institute = FakeInstituteCache([_institute()])
    factory.caches.session_store = session_store
    factory.id_provider = FakeIdProvider(now_value=_NOW, operation_ids=[])
    factory.operation_session_ttl_seconds = 600

    command = PollOperationCommand(
        authenticate_consumer=_authenticate_consumer(),
        institute_catalog=factory.caches.institute,
        factory=factory,
        session_store=session_store,
        id_provider=factory.id_provider,
    )

    asyncio.run(command("op-1", _poll_operation_request(), presented_api_key=_API_KEY))

    factory.get_banking_connector.assert_awaited_once()


def test_poll_operation_propagates_gateway_misconfigured_error() -> None:
    session_store = FakeOperationSessionStore([_pending_session()])
    factory = _make_misconfigured_factory()
    factory.caches.session_store = session_store

    command = PollOperationCommand(
        authenticate_consumer=_authenticate_consumer(),
        institute_catalog=factory.caches.institute,
        factory=factory,
        session_store=session_store,
        id_provider=factory.id_provider,
    )

    with pytest.raises(GatewayMisconfiguredError):
        asyncio.run(
            command("op-1", _poll_operation_request(), presented_api_key=_API_KEY)
        )


def _poll_operation_request() -> PollOperationInput:
    return PollOperationInput(
        blz=BankLeitzahl("12345678"),
        user_id="bank-user",
        password="bank-password",
    )


# ---------------------------------------------------------------------------
# Auth-before-connector ordering tests
#
# Verifies that authentication is checked BEFORE get_banking_connector() is
# called, so an invalid API key never triggers a DB round-trip.
# ---------------------------------------------------------------------------


def _make_factory_tracking_call_order(
    connector: FakeBankingConnector,
) -> tuple[AsyncMock, list[str]]:
    """Return a factory mock and a shared call-order log.

    The log records 'get_banking_connector' whenever that method is awaited,
    so tests can assert it was not called before authentication failed.
    """
    call_log: list[str] = []

    async def _get_banking_connector_tracked():
        call_log.append("get_banking_connector")
        return connector

    factory = AsyncMock()
    factory.get_banking_connector = AsyncMock(
        side_effect=_get_banking_connector_tracked
    )
    factory.caches.institute = FakeInstituteCache([_institute()])
    factory.caches.session_store = FakeOperationSessionStore()
    factory.id_provider = FakeIdProvider(now_value=_NOW, operation_ids=["op-1"])
    factory.operation_session_ttl_seconds = 600
    return factory, call_log


def _bad_api_key() -> str:
    return "invalid.bad-key"


def test_list_accounts_does_not_call_get_banking_connector_on_auth_failure() -> None:
    """get_banking_connector() must NOT be called when authentication fails.

    Validates the auth-before-connector ordering in ListAccountsCommand.__call__.
    """
    connector = FakeBankingConnector(
        accounts_results=[AccountsResult(status=OperationStatus.COMPLETED, accounts=[])]
    )
    factory, call_log = _make_factory_tracking_call_order(connector)
    command = ListAccountsCommand(
        authenticate_consumer=_authenticate_consumer(),
        institute_catalog=factory.caches.institute,
        factory=factory,
        session_store=factory.caches.session_store,
        id_provider=factory.id_provider,
    )

    from gateway.application.common import UnauthorizedError

    with pytest.raises(UnauthorizedError):
        asyncio.run(command(_list_accounts_request(), presented_api_key=_bad_api_key()))

    assert "get_banking_connector" not in call_log, (
        "get_banking_connector was called before authentication completed"
    )


def test_fetch_transactions_does_not_call_get_banking_connector_on_auth_failure() -> (
    None
):
    """get_banking_connector() must NOT be called when authentication fails.

    Validates the auth-before-connector ordering in FetchTransactionsCommand.__call__.
    """
    connector = FakeBankingConnector(
        transactions_results=[
            TransactionsResult(status=OperationStatus.COMPLETED, transactions=[])
        ]
    )
    factory, call_log = _make_factory_tracking_call_order(connector)
    command = FetchTransactionsCommand(
        authenticate_consumer=_authenticate_consumer(),
        institute_catalog=factory.caches.institute,
        factory=factory,
        session_store=factory.caches.session_store,
        id_provider=factory.id_provider,
    )

    from gateway.application.common import UnauthorizedError

    with pytest.raises(UnauthorizedError):
        asyncio.run(
            command(_fetch_transactions_request(), presented_api_key=_bad_api_key())
        )

    assert "get_banking_connector" not in call_log, (
        "get_banking_connector was called before authentication completed"
    )


def test_get_balances_does_not_call_get_banking_connector_on_auth_failure() -> None:
    """get_banking_connector() must NOT be called when authentication fails.

    Validates the auth-before-connector ordering in GetBalancesCommand.__call__.
    """
    connector = FakeBankingConnector(
        balances_results=[BalancesResult(status=OperationStatus.COMPLETED, balances=[])]
    )
    factory, call_log = _make_factory_tracking_call_order(connector)
    command = GetBalancesCommand(
        authenticate_consumer=_authenticate_consumer(),
        institute_catalog=factory.caches.institute,
        factory=factory,
        session_store=factory.caches.session_store,
        id_provider=factory.id_provider,
    )

    from gateway.application.common import UnauthorizedError

    with pytest.raises(UnauthorizedError):
        asyncio.run(command(_get_balances_request(), presented_api_key=_bad_api_key()))

    assert "get_banking_connector" not in call_log, (
        "get_banking_connector was called before authentication completed"
    )


def test_get_tan_methods_does_not_call_get_banking_connector_on_auth_failure() -> None:
    """get_banking_connector() must NOT be called when authentication fails.

    Validates the auth-before-connector ordering in GetTanMethodsCommand.__call__.
    """
    connector = FakeBankingConnector(
        tan_methods_results=[
            TanMethodsResult(status=OperationStatus.COMPLETED, methods=[])
        ]
    )
    factory, call_log = _make_factory_tracking_call_order(connector)
    command = GetTanMethodsCommand(
        authenticate_consumer=_authenticate_consumer(),
        institute_catalog=factory.caches.institute,
        factory=factory,
        session_store=factory.caches.session_store,
        id_provider=factory.id_provider,
    )

    from gateway.application.common import UnauthorizedError

    with pytest.raises(UnauthorizedError):
        asyncio.run(
            command(_get_tan_methods_request(), presented_api_key=_bad_api_key())
        )

    assert "get_banking_connector" not in call_log, (
        "get_banking_connector was called before authentication completed"
    )
