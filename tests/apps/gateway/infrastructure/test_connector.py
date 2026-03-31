"""Tests for the Geldstrom anti-corruption connector."""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from gateway.application.common import BankUpstreamUnavailableError
from gateway.domain.banking_gateway import (
    BankLeitzahl,
    FinTSInstitute,
    OperationStatus,
    PresentedBankCredentials,
    RequestedIban,
)
from gateway.infrastructure.banking.geldstrom.connector import GeldstromBankingConnector
from gateway.infrastructure.banking.geldstrom.exceptions import (
    GeldstromPendingConfirmation,
)
from geldstrom.domain import (
    Account,
    AccountCapabilities,
    AccountOwner,
    BalanceAmount,
    BalanceSnapshot,
    BankRoute,
    TANMethodType,
    TransactionEntry,
    TransactionFeed,
)
from geldstrom.domain import (
    TANMethod as GeldstromTanMethod,
)
from geldstrom.infrastructure.fints.session import FinTSSessionState


class StubClientFactory:
    def __init__(self, clients: list[StubClient]) -> None:
        self._clients = clients

    def create(self, credentials, session_state=None):
        client = self._clients.pop(0)
        client.received_credentials = credentials
        client.received_session_state = session_state
        return client


class StubClient:
    def __init__(
        self,
        *,
        accounts: list[Account] | None = None,
        balances: list[BalanceSnapshot] | None = None,
        feed: TransactionFeed | None = None,
        tan_methods: list[GeldstromTanMethod] | None = None,
        pending_on: str | None = None,
        session_state: FinTSSessionState | None = None,
    ) -> None:
        self._accounts = accounts or []
        self._balances = balances or []
        self._feed = feed
        self._tan_methods = tan_methods or []
        self._pending_on = pending_on
        self._session_state = session_state
        self.received_credentials = None
        self.received_session_state = None

    def list_accounts(self) -> list[Account]:
        if self._pending_on == "accounts":
            raise GeldstromPendingConfirmation(
                self._session_state or _session_state(),
                datetime(2026, 3, 7, 12, 5, tzinfo=UTC),
            )
        return self._accounts

    def get_balances(self) -> list[BalanceSnapshot]:
        if self._pending_on == "balances":
            raise GeldstromPendingConfirmation(
                self._session_state or _session_state(),
                datetime(2026, 3, 7, 12, 5, tzinfo=UTC),
            )
        return self._balances

    def get_transactions(
        self, account, start_date=None, end_date=None
    ) -> TransactionFeed:
        if self._pending_on == "transactions":
            raise GeldstromPendingConfirmation(
                self._session_state or _session_state(),
                datetime(2026, 3, 7, 12, 5, tzinfo=UTC),
            )
        assert self._feed is not None
        return self._feed

    def get_tan_methods(self) -> list[GeldstromTanMethod]:
        if self._pending_on == "tan_methods":
            raise GeldstromPendingConfirmation(
                self._session_state or _session_state(),
                datetime(2026, 3, 7, 12, 5, tzinfo=UTC),
            )
        return self._tan_methods

    @property
    def session_state(self):
        return self._session_state


def test_connector_maps_completed_account_listing() -> None:
    connector = GeldstromBankingConnector(
        "product-key-1",
        product_version="0.0.1",
        client_factory=StubClientFactory([StubClient(accounts=[_account()])]),
    )

    result = asyncio.run(connector.list_accounts(_institute(), _credentials()))

    assert result.status is OperationStatus.COMPLETED
    assert result.accounts == [
        {
            "account_id": "acc-1",
            "iban": "DE89370400440532013000",
            "bic": "GENODEF1ABC",
            "currency": "EUR",
            "product_name": "Girokonto",
            "owner_name": "Max Mustermann",
            "bank_code": "12345678",
            "country_code": "DE",
            "capabilities": {
                "balance": False,
                "transactions": True,
                "holdings": False,
                "scheduled_debits": False,
            },
            "labels": ["giro"],
            "metadata": {"source": "test"},
        }
    ]


def test_connector_serializes_pending_transactions_for_resume() -> None:
    connector = GeldstromBankingConnector(
        "product-key-1",
        product_version="0.0.1",
        client_factory=StubClientFactory(
            [
                StubClient(
                    accounts=[_account()],
                    pending_on="transactions",
                    session_state=_session_state(),
                ),
                StubClient(
                    accounts=[_account()], feed=_feed(), session_state=_session_state()
                ),
            ]
        ),
    )

    first = asyncio.run(
        connector.fetch_transactions(
            _institute(),
            _credentials(),
            RequestedIban("DE89370400440532013000"),
            date(2026, 1, 1),
            date(2026, 2, 1),
        )
    )
    resumed = asyncio.run(connector.resume_operation(first.session_state))

    assert first.status is OperationStatus.PENDING_CONFIRMATION
    assert resumed.status is OperationStatus.COMPLETED
    assert resumed.result_payload == {
        "transactions": [
            {
                "transaction_id": "txn-1",
                "account_id": "acc-1",
                "booking_date": "2026-01-02",
                "value_date": "2026-01-02",
                "amount": "12.34",
                "currency": "EUR",
                "purpose": "Invoice",
                "counterpart_name": "Example GmbH",
                "counterpart_iban": "DE12500105170648489890",
                "metadata": {"booking_text": "SEPA"},
                "feed_start_date": "2026-01-01",
                "feed_end_date": "2026-02-01",
                "has_more": False,
            }
        ]
    }


def test_connector_maps_tan_methods() -> None:
    connector = GeldstromBankingConnector(
        "product-key-1",
        product_version="0.0.1",
        client_factory=StubClientFactory(
            [
                StubClient(
                    tan_methods=[
                        GeldstromTanMethod(
                            code="942",
                            name="App-Freigabe",
                            method_type=TANMethodType.DECOUPLED,
                            is_decoupled=True,
                        )
                    ]
                )
            ]
        ),
    )

    result = asyncio.run(connector.get_tan_methods(_institute(), _credentials()))

    assert result.status is OperationStatus.COMPLETED
    assert [method.method_id for method in result.methods] == ["942"]


def test_connector_maps_completed_balance_query() -> None:
    connector = GeldstromBankingConnector(
        "product-key-1",
        product_version="0.0.1",
        client_factory=StubClientFactory([StubClient(balances=[_balance_snapshot()])]),
    )

    result = asyncio.run(connector.get_balances(_institute(), _credentials()))

    assert result.status is OperationStatus.COMPLETED
    assert result.balances == [
        {
            "account_id": "acc-1",
            "as_of": "2026-03-20T12:00:00+00:00",
            "booked_amount": "1234.56",
            "booked_currency": "EUR",
            "pending_amount": "10.00",
            "pending_currency": "EUR",
            "available_amount": None,
            "available_currency": None,
        }
    ]


def test_connector_serializes_pending_balances_for_resume() -> None:
    connector = GeldstromBankingConnector(
        "product-key-1",
        product_version="0.0.1",
        client_factory=StubClientFactory(
            [
                StubClient(pending_on="balances", session_state=_session_state()),
                StubClient(
                    balances=[_balance_snapshot()], session_state=_session_state()
                ),
            ]
        ),
    )

    first = asyncio.run(connector.get_balances(_institute(), _credentials()))
    resumed = asyncio.run(connector.resume_operation(first.session_state))

    assert first.status is OperationStatus.PENDING_CONFIRMATION
    assert resumed.status is OperationStatus.COMPLETED
    assert resumed.result_payload == {
        "balances": [
            {
                "account_id": "acc-1",
                "as_of": "2026-03-20T12:00:00+00:00",
                "booked_amount": "1234.56",
                "booked_currency": "EUR",
                "pending_amount": "10.00",
                "pending_currency": "EUR",
                "available_amount": None,
                "available_currency": None,
            }
        ]
    }


def test_connector_returns_empty_balances_list() -> None:
    connector = GeldstromBankingConnector(
        "product-key-1",
        product_version="0.0.1",
        client_factory=StubClientFactory([StubClient(balances=[])]),
    )

    result = asyncio.run(connector.get_balances(_institute(), _credentials()))

    assert result.status is OperationStatus.COMPLETED
    assert result.balances == []


def test_connector_rejects_http_pin_tan_url() -> None:
    connector = GeldstromBankingConnector(
        "product-key-1",
        product_version="0.0.1",
        client_factory=StubClientFactory([StubClient()]),
    )
    insecure_institute = FinTSInstitute(
        blz=BankLeitzahl("12345678"),
        bic="GENODEF1ABC",
        name="Insecure Bank",
        city="Berlin",
        organization="Example Org",
        pin_tan_url="http://insecure.bank.example/fints",
        fints_version="3.0",
        last_source_update=date(2026, 3, 7),
    )

    with pytest.raises(BankUpstreamUnavailableError, match="not HTTPS"):
        asyncio.run(connector.list_accounts(insecure_institute, _credentials()))


def test_connector_rejects_missing_pin_tan_url() -> None:
    connector = GeldstromBankingConnector(
        "product-key-1",
        product_version="0.0.1",
        client_factory=StubClientFactory([StubClient()]),
    )
    no_url_institute = FinTSInstitute(
        blz=BankLeitzahl("12345678"),
        bic="GENODEF1ABC",
        name="No URL Bank",
        city="Berlin",
        organization="Example Org",
        pin_tan_url=None,
        fints_version="3.0",
        last_source_update=date(2026, 3, 7),
    )

    with pytest.raises(BankUpstreamUnavailableError, match="PIN/TAN endpoint"):
        asyncio.run(connector.list_accounts(no_url_institute, _credentials()))


def _credentials() -> PresentedBankCredentials:
    return PresentedBankCredentials(
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
        last_source_update=date(2026, 3, 7),
    )


def _account() -> Account:
    return Account(
        account_id="acc-1",
        iban="DE89370400440532013000",
        bic="GENODEF1ABC",
        currency="EUR",
        product_name="Girokonto",
        owner=AccountOwner(name="Max Mustermann"),
        bank_route=BankRoute(country_code="DE", bank_code="12345678"),
        capabilities=AccountCapabilities(can_list_transactions=True),
        raw_labels=("giro",),
        metadata={"source": "test"},
    )


def _feed() -> TransactionFeed:
    return TransactionFeed(
        account_id="acc-1",
        entries=[
            TransactionEntry(
                entry_id="txn-1",
                booking_date=date(2026, 1, 2),
                value_date=date(2026, 1, 2),
                amount=Decimal("12.34"),
                currency="EUR",
                purpose="Invoice",
                counterpart_name="Example GmbH",
                counterpart_iban="DE12500105170648489890",
                metadata={"booking_text": "SEPA"},
            )
        ],
        start_date=date(2026, 1, 1),
        end_date=date(2026, 2, 1),
    )


def _session_state() -> FinTSSessionState:
    return FinTSSessionState(
        route=BankRoute(country_code="DE", bank_code="12345678"),
        user_id="bank-user",
        system_id="system-1",
        client_blob=b"blob",
    )


def _balance_snapshot() -> BalanceSnapshot:
    return BalanceSnapshot(
        account_id="acc-1",
        as_of=datetime(2026, 3, 20, 12, 0, tzinfo=UTC),
        booked=BalanceAmount(amount=Decimal("1234.56"), currency="EUR"),
        pending=BalanceAmount(amount=Decimal("10.00"), currency="EUR"),
    )
