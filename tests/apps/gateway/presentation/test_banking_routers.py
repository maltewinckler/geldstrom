"""Tests for the banking routers: accounts, transactions, tan-methods, and operations."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from starlette.testclient import TestClient

from gateway.application.banking.commands.fetch_transactions import (
    FetchTransactionsCommand,
)
from gateway.application.banking.commands.get_balances import GetBalancesCommand
from gateway.application.banking.commands.get_tan_methods import GetTanMethodsCommand
from gateway.application.banking.commands.list_accounts import ListAccountsCommand
from gateway.application.banking.dtos.fetch_transactions import (
    TransactionsResultEnvelope,
)
from gateway.application.banking.dtos.get_balances import BalancesResultEnvelope
from gateway.application.banking.dtos.get_operation_status import (
    OperationStatusEnvelope,
)
from gateway.application.banking.dtos.get_tan_methods import TanMethodsResultEnvelope
from gateway.application.banking.dtos.list_accounts import ListAccountsResultEnvelope
from gateway.application.banking.queries.get_operation_status import (
    GetOperationStatusQuery,
)
from gateway.domain.banking_gateway import OperationStatus, TanMethod
from gateway.presentation.http.dependencies import get_factory
from gateway.presentation.http.routers import (
    accounts,
    balances,
    operations,
    tan_methods,
    transactions,
)

_AUTH = {"Authorization": "Bearer test-api-key"}

_FUTURE = datetime(2030, 1, 1, tzinfo=UTC)


def _make_app(router) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_factory] = lambda: MagicMock()
    return app


# ---------------------------------------------------------------------------
# Accounts router
# ---------------------------------------------------------------------------

_ACCOUNTS_BODY = {
    "protocol": "fints",
    "blz": "20070024",
    "user_id": "testuser",
    "password": "secret",
}


def test_list_accounts_returns_200_when_completed() -> None:
    envelope = ListAccountsResultEnvelope(
        status=OperationStatus.COMPLETED,
        accounts=[{"iban": "DE00000000000000000000"}],
    )
    use_case = AsyncMock(return_value=envelope)
    with patch.object(ListAccountsCommand, "from_factory", return_value=use_case):
        client = TestClient(_make_app(accounts.router))
        resp = client.post("/v1/banking/accounts", json=_ACCOUNTS_BODY, headers=_AUTH)

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    assert body["accounts"] == [{"iban": "DE00000000000000000000"}]


def test_list_accounts_returns_202_when_pending() -> None:
    envelope = ListAccountsResultEnvelope(
        status=OperationStatus.PENDING_CONFIRMATION,
        operation_id="op-1",
        expires_at=_FUTURE,
    )
    use_case = AsyncMock(return_value=envelope)
    with patch.object(ListAccountsCommand, "from_factory", return_value=use_case):
        client = TestClient(_make_app(accounts.router))
        resp = client.post("/v1/banking/accounts", json=_ACCOUNTS_BODY, headers=_AUTH)

    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "pending_confirmation"
    assert body["operation_id"] == "op-1"


def test_list_accounts_returns_401_without_auth() -> None:
    client = TestClient(_make_app(accounts.router), raise_server_exceptions=False)
    resp = client.post("/v1/banking/accounts", json=_ACCOUNTS_BODY)
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Transactions router
# ---------------------------------------------------------------------------

_TRANSACTIONS_BODY = {
    "protocol": "fints",
    "blz": "20070024",
    "user_id": "testuser",
    "password": "secret",
    "iban": "DE00000000000000000000",
}


def test_fetch_transactions_returns_200_when_completed() -> None:
    envelope = TransactionsResultEnvelope(
        status=OperationStatus.COMPLETED,
        transactions=[{"amount": "100.00"}],
    )
    use_case = AsyncMock(return_value=envelope)
    with patch.object(FetchTransactionsCommand, "from_factory", return_value=use_case):
        client = TestClient(_make_app(transactions.router))
        resp = client.post(
            "/v1/banking/transactions", json=_TRANSACTIONS_BODY, headers=_AUTH
        )

    assert resp.status_code == 200
    assert resp.json()["transactions"] == [{"amount": "100.00"}]


def test_fetch_transactions_returns_202_when_pending() -> None:
    envelope = TransactionsResultEnvelope(
        status=OperationStatus.PENDING_CONFIRMATION,
        operation_id="op-2",
        expires_at=_FUTURE,
    )
    use_case = AsyncMock(return_value=envelope)
    with patch.object(FetchTransactionsCommand, "from_factory", return_value=use_case):
        client = TestClient(_make_app(transactions.router))
        resp = client.post(
            "/v1/banking/transactions", json=_TRANSACTIONS_BODY, headers=_AUTH
        )

    assert resp.status_code == 202
    assert resp.json()["operation_id"] == "op-2"


# ---------------------------------------------------------------------------
# TAN methods router
# ---------------------------------------------------------------------------

_TAN_METHODS_BODY = {
    "protocol": "fints",
    "blz": "20070024",
    "user_id": "testuser",
    "password": "secret",
}


def test_get_tan_methods_returns_200_when_completed() -> None:
    envelope = TanMethodsResultEnvelope(
        status=OperationStatus.COMPLETED,
        methods=[TanMethod(method_id="900", display_name="pushTAN", is_decoupled=True)],
    )
    use_case = AsyncMock(return_value=envelope)
    with patch.object(GetTanMethodsCommand, "from_factory", return_value=use_case):
        client = TestClient(_make_app(tan_methods.router))
        resp = client.post(
            "/v1/banking/tan-methods", json=_TAN_METHODS_BODY, headers=_AUTH
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["methods"] == [{"method_id": "900", "display_name": "pushTAN"}]


def test_get_tan_methods_returns_202_when_pending() -> None:
    envelope = TanMethodsResultEnvelope(
        status=OperationStatus.PENDING_CONFIRMATION,
        operation_id="op-3",
        expires_at=_FUTURE,
    )
    use_case = AsyncMock(return_value=envelope)
    with patch.object(GetTanMethodsCommand, "from_factory", return_value=use_case):
        client = TestClient(_make_app(tan_methods.router))
        resp = client.post(
            "/v1/banking/tan-methods", json=_TAN_METHODS_BODY, headers=_AUTH
        )

    assert resp.status_code == 202
    assert resp.json()["operation_id"] == "op-3"


# ---------------------------------------------------------------------------
# Operations router
# ---------------------------------------------------------------------------


def test_get_operation_status_returns_200() -> None:
    op_uuid = "12345678-1234-5678-1234-567812345678"
    envelope = OperationStatusEnvelope(
        status=OperationStatus.COMPLETED,
        operation_id=op_uuid,
        result_payload={"accounts": []},
    )
    use_case = AsyncMock(return_value=envelope)
    with patch.object(GetOperationStatusQuery, "from_factory", return_value=use_case):
        client = TestClient(_make_app(operations.router))
        resp = client.get(f"/v1/banking/operations/{op_uuid}", headers=_AUTH)

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    assert body["operation_id"] == op_uuid


def test_get_operation_status_returns_401_without_auth() -> None:
    client = TestClient(_make_app(operations.router), raise_server_exceptions=False)
    op_uuid = "12345678-1234-5678-1234-567812345678"
    resp = client.get(f"/v1/banking/operations/{op_uuid}")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Balances router
# ---------------------------------------------------------------------------

_BALANCES_BODY = {
    "protocol": "fints",
    "blz": "20070024",
    "user_id": "testuser",
    "password": "secret",
}

_BALANCE_ENTRY = {
    "account_id": "acc-1",
    "as_of": "2026-03-20T12:00:00+00:00",
    "booked_amount": "500.00",
    "booked_currency": "EUR",
    "pending_amount": None,
    "pending_currency": None,
    "available_amount": None,
    "available_currency": None,
}


def test_get_balances_returns_200_when_completed() -> None:
    envelope = BalancesResultEnvelope(
        status=OperationStatus.COMPLETED,
        balances=[_BALANCE_ENTRY],
    )
    use_case = AsyncMock(return_value=envelope)
    with patch.object(GetBalancesCommand, "from_factory", return_value=use_case):
        client = TestClient(_make_app(balances.router))
        resp = client.post("/v1/banking/balances", json=_BALANCES_BODY, headers=_AUTH)

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    assert body["balances"] == [_BALANCE_ENTRY]


def test_get_balances_returns_202_when_pending() -> None:
    envelope = BalancesResultEnvelope(
        status=OperationStatus.PENDING_CONFIRMATION,
        operation_id="op-5",
        expires_at=_FUTURE,
    )
    use_case = AsyncMock(return_value=envelope)
    with patch.object(GetBalancesCommand, "from_factory", return_value=use_case):
        client = TestClient(_make_app(balances.router))
        resp = client.post("/v1/banking/balances", json=_BALANCES_BODY, headers=_AUTH)

    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "pending_confirmation"
    assert body["operation_id"] == "op-5"


def test_get_balances_returns_401_without_auth() -> None:
    client = TestClient(_make_app(balances.router), raise_server_exceptions=False)
    resp = client.post("/v1/banking/balances", json=_BALANCES_BODY)
    assert resp.status_code == 401
