"""Tests for the Geldstrom anti-corruption connector."""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from decimal import Decimal

from pydantic import SecretStr

from gateway.domain.banking_gateway import (
    OperationStatus,
    PresentedBankCredentials,
    PresentedBankPassword,
    PresentedBankUserId,
    RequestedIban,
)
from gateway.domain.institution_catalog import (
    BankLeitzahl,
    Bic,
    FinTSInstitute,
    InstituteEndpoint,
)
from gateway.infrastructure.banking.geldstrom.connector import GeldstromBankingConnector
from gateway.infrastructure.banking.geldstrom.exceptions import (
    GeldstromPendingConfirmation,
)
from geldstrom.domain import (
    Account,
    AccountCapabilities,
    AccountOwner,
    BankRoute,
    TANMethodType,
    TransactionEntry,
    TransactionFeed,
)
from geldstrom.domain import (
    TANMethod as GeldstromTanMethod,
)
from geldstrom.infrastructure.fints.session import FinTSSessionState
from tests.apps.gateway.fakes import FakeProductKeyProvider


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
        feed: TransactionFeed | None = None,
        tan_methods: list[GeldstromTanMethod] | None = None,
        pending_on: str | None = None,
        session_state: FinTSSessionState | None = None,
    ) -> None:
        self._accounts = accounts or []
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
        FakeProductKeyProvider("product-key-1"),
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
        FakeProductKeyProvider("product-key-1"),
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
        FakeProductKeyProvider("product-key-1"),
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


def _credentials() -> PresentedBankCredentials:
    return PresentedBankCredentials(
        user_id=PresentedBankUserId(SecretStr("bank-user")),
        password=PresentedBankPassword(SecretStr("bank-password")),
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
        last_source_update=date(2026, 3, 7),
        source_row_checksum="checksum-1",
        source_payload={"row": 1},
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
