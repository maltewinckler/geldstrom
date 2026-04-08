"""Tests for the Geldstrom anti-corruption connector."""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock

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
from geldstrom.domain import (
    Account,
    AccountCapabilities,
    AccountOwner,
    BalanceAmount,
    BalanceSnapshot,
    BankRoute,
    TransactionEntry,
    TransactionFeed,
)
from geldstrom.infrastructure.fints.challenge import DecoupledTANPending
from geldstrom.infrastructure.fints.session_snapshot import DecoupledSessionSnapshot
from geldstrom.infrastructure.fints.tan import (
    TANMethod as GeldstromTanMethod,
)


class _FakeChallenge:
    """Minimal Challenge stub for DecoupledTANPending."""

    @property
    def challenge_type(self):
        from geldstrom.infrastructure.fints.challenge import ChallengeType

        return ChallengeType.DECOUPLED

    @property
    def challenge_text(self):
        return "Confirm in app"

    @property
    def challenge_html(self):
        return None

    @property
    def challenge_data(self):
        return None

    @property
    def is_decoupled(self):
        return True

    def get_data(self):
        return b""


def _make_snapshot_bytes(operation_type: str = "accounts", **meta) -> bytes:
    """Build a canned DecoupledSessionSnapshot for testing."""
    return DecoupledSessionSnapshot(
        dialog_snapshot={
            "dialog_id": "dialog-1",
            "message_number": 3,
            "country_identifier": "280",
            "bank_code": "12345678",
            "user_id": "bank-user",
            "customer_id": "bank-user",
            "system_id": "system-1",
            "product_name": "test-product",
            "product_version": "0.0.1",
            "security_function": "942",
        },
        task_reference="task-ref-1",
        fints_session_state=b"\x00" * 16,
        server_url="https://bank.example/fints",
        operation_type=operation_type,
        operation_meta=meta,
    ).serialize()


class StubClientFactory:
    def __init__(self, clients: list) -> None:
        self._clients = clients

    def create(self, credentials, session_state=None):
        client = self._clients.pop(0)
        client.received_credentials = credentials
        client.received_session_state = session_state
        return client


class StubClient:
    """Stub that optionally raises DecoupledTANPending and supports snapshot_pending()."""

    def __init__(
        self,
        *,
        accounts: list[Account] | None = None,
        balances: list[BalanceSnapshot] | None = None,
        feed: TransactionFeed | None = None,
        tan_methods: list[GeldstromTanMethod] | None = None,
        pending_on: str | None = None,
        snapshot_bytes: bytes | None = None,
    ) -> None:
        self._accounts = accounts or []
        self._balances = balances or []
        self._feed = feed
        self._tan_methods = tan_methods or []
        self._pending_on = pending_on
        self._snapshot_bytes = snapshot_bytes
        self.received_credentials = None
        self.received_session_state = None

    def _maybe_raise(self, operation: str):
        if self._pending_on == operation:
            raise DecoupledTANPending(_FakeChallenge(), "task-ref-1")

    def list_accounts(self) -> list[Account]:
        self._maybe_raise("accounts")
        return self._accounts

    def get_balances(self) -> list[BalanceSnapshot]:
        self._maybe_raise("balances")
        return self._balances

    def get_transactions(
        self, account, start_date=None, end_date=None
    ) -> TransactionFeed:
        self._maybe_raise("transactions")
        assert self._feed is not None
        return self._feed

    def get_tan_methods(self) -> list[GeldstromTanMethod]:
        self._maybe_raise("tan_methods")
        return self._tan_methods

    def snapshot_pending(self) -> bytes:
        if self._snapshot_bytes is not None:
            return self._snapshot_bytes
        return _make_snapshot_bytes("accounts")

    @property
    def session_state(self):
        return None


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


def test_connector_returns_pending_with_snapshot_for_transactions() -> None:
    snapshot = _make_snapshot_bytes(
        "transactions",
        account_id="acc-1",
        start_date="2026-01-01",
        end_date="2026-02-01",
    )
    connector = GeldstromBankingConnector(
        "product-key-1",
        product_version="0.0.1",
        client_factory=StubClientFactory(
            [
                StubClient(
                    accounts=[_account()],
                    pending_on="transactions",
                    snapshot_bytes=snapshot,
                ),
            ]
        ),
    )

    result = asyncio.run(
        connector.fetch_transactions(
            _institute(),
            _credentials(),
            RequestedIban("DE89370400440532013000"),
            date(2026, 1, 1),
            date(2026, 2, 1),
        )
    )

    assert result.status is OperationStatus.PENDING_CONFIRMATION
    assert result.session_state is not None
    # Session state is a valid DecoupledSessionSnapshot
    restored = DecoupledSessionSnapshot.deserialize(result.session_state)
    assert restored.operation_type == "transactions"
    assert restored.task_reference == "task-ref-1"


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


def test_connector_returns_pending_with_snapshot_for_balances() -> None:
    snapshot = _make_snapshot_bytes("balances")
    connector = GeldstromBankingConnector(
        "product-key-1",
        product_version="0.0.1",
        client_factory=StubClientFactory(
            [
                StubClient(pending_on="balances", snapshot_bytes=snapshot),
            ]
        ),
    )

    result = asyncio.run(connector.get_balances(_institute(), _credentials()))

    assert result.status is OperationStatus.PENDING_CONFIRMATION
    assert result.session_state is not None
    restored = DecoupledSessionSnapshot.deserialize(result.session_state)
    assert restored.operation_type == "balances"


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


def _balance_snapshot() -> BalanceSnapshot:
    return BalanceSnapshot(
        account_id="acc-1",
        as_of=datetime(2026, 3, 20, 12, 0, tzinfo=UTC),
        booked=BalanceAmount(amount=Decimal("1234.56"), currency="EUR"),
        pending=BalanceAmount(amount=Decimal("10.00"), currency="EUR"),
    )


# ---------------------------------------------------------------------------
# Pending snapshot tests (DecoupledTANPending → snapshot_pending → snapshot bytes)
# ---------------------------------------------------------------------------


def test_pending_accounts_returns_snapshot() -> None:
    snapshot = _make_snapshot_bytes("accounts")
    connector = GeldstromBankingConnector(
        "product-key-1",
        product_version="0.0.1",
        client_factory=StubClientFactory(
            [StubClient(pending_on="accounts", snapshot_bytes=snapshot)]
        ),
    )

    result = asyncio.run(connector.list_accounts(_institute(), _credentials()))

    assert result.status is OperationStatus.PENDING_CONFIRMATION
    restored = DecoupledSessionSnapshot.deserialize(result.session_state)
    assert restored.operation_type == "accounts"


def test_pending_tan_methods_returns_snapshot() -> None:
    snapshot = _make_snapshot_bytes("tan_methods")
    connector = GeldstromBankingConnector(
        "product-key-1",
        product_version="0.0.1",
        client_factory=StubClientFactory(
            [StubClient(pending_on="tan_methods", snapshot_bytes=snapshot)]
        ),
    )

    result = asyncio.run(connector.get_tan_methods(_institute(), _credentials()))

    assert result.status is OperationStatus.PENDING_CONFIRMATION
    restored = DecoupledSessionSnapshot.deserialize(result.session_state)
    assert restored.operation_type == "tan_methods"


# ---------------------------------------------------------------------------
# Resume tests (snapshot-based with mocked FinTSConnectionHelper)
# ---------------------------------------------------------------------------


def _make_resume_connector() -> GeldstromBankingConnector:
    return GeldstromBankingConnector(
        "product-key-1",
        product_version="0.0.1",
        client_factory=StubClientFactory([]),
    )


def test_resume_returns_pending_when_poll_returns_none(monkeypatch) -> None:
    """poll_decoupled_once returning None means still pending."""
    connector = _make_resume_connector()
    session_state = _make_snapshot_bytes("accounts")

    mock_dialog = MagicMock()
    mock_dialog.poll_decoupled_once.return_value = None
    mock_dialog.snapshot.return_value = MagicMock(
        to_dict=MagicMock(return_value={"dialog_id": "d1", "message_number": 4})
    )
    mock_dialog.is_open = False

    mock_ctx = MagicMock()
    mock_ctx.dialog = mock_dialog
    mock_ctx.connection = MagicMock()

    mock_helper_cls = MagicMock()
    mock_helper_instance = mock_helper_cls.return_value
    mock_helper_instance.resume_for_polling.return_value = mock_ctx
    mock_helper_instance.create_session_state.return_value = MagicMock(
        serialize=MagicMock(return_value=b"\x00" * 16)
    )

    monkeypatch.setattr(
        "gateway.infrastructure.banking.geldstrom.connector.FinTSConnectionHelper",
        mock_helper_cls,
    )

    result = asyncio.run(
        connector.resume_operation(session_state, _credentials(), _institute())
    )

    assert result.status is OperationStatus.PENDING_CONFIRMATION
    assert result.session_state is not None


def test_resume_returns_failed_on_poll_error(monkeypatch) -> None:
    """poll_decoupled_once raising ValueError → FAILED."""
    connector = _make_resume_connector()
    session_state = _make_snapshot_bytes("accounts")

    mock_dialog = MagicMock()
    mock_dialog.poll_decoupled_once.side_effect = ValueError("TAN timed out")
    mock_dialog.is_open = False

    mock_ctx = MagicMock()
    mock_ctx.dialog = mock_dialog
    mock_ctx.connection = MagicMock()

    mock_helper_cls = MagicMock()
    mock_helper_cls.return_value.resume_for_polling.return_value = mock_ctx

    monkeypatch.setattr(
        "gateway.infrastructure.banking.geldstrom.connector.FinTSConnectionHelper",
        mock_helper_cls,
    )

    result = asyncio.run(
        connector.resume_operation(session_state, _credentials(), _institute())
    )

    assert result.status is OperationStatus.FAILED
    assert "TAN timed out" in (result.failure_reason or "")


def test_resume_returns_completed_on_approval(monkeypatch) -> None:
    """poll_decoupled_once returning data → COMPLETED with parsed payload."""
    connector = _make_resume_connector()
    session_state = _make_snapshot_bytes("accounts")

    mock_response = MagicMock()
    mock_dialog = MagicMock()
    mock_dialog.poll_decoupled_once.return_value = mock_response
    mock_dialog.is_open = False

    mock_ctx = MagicMock()
    mock_ctx.dialog = mock_dialog
    mock_ctx.connection = MagicMock()

    mock_helper_cls = MagicMock()
    mock_helper_cls.return_value.resume_for_polling.return_value = mock_ctx

    monkeypatch.setattr(
        "gateway.infrastructure.banking.geldstrom.connector.FinTSConnectionHelper",
        mock_helper_cls,
    )

    # Mock _parse_approved_response to avoid deep FinTS service dependencies
    monkeypatch.setattr(
        connector,
        "_parse_approved_response",
        lambda snapshot, response, ctx: {"accounts": [{"account_id": "acc-1"}]},
    )

    result = asyncio.run(
        connector.resume_operation(session_state, _credentials(), _institute())
    )

    assert result.status is OperationStatus.COMPLETED
    assert result.result_payload == {"accounts": [{"account_id": "acc-1"}]}


def test_resume_rejects_corrupt_session_state() -> None:
    """Corrupt session_state raises InternalError."""
    from gateway.application.common import InternalError

    connector = _make_resume_connector()

    with pytest.raises(InternalError, match="Unable to deserialize"):
        asyncio.run(
            connector.resume_operation(b"not-valid-json", _credentials(), _institute())
        )
