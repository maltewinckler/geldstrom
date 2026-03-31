"""Unit tests covering domain-layer value objects."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from geldstrom.domain import (
    Account,
    AccountCapabilities,
    AccountOwner,
    BalanceAmount,
    BalanceSnapshot,
    BankCapabilities,
    BankRoute,
    TransactionEntry,
    TransactionFeed,
)
from geldstrom.infrastructure.fints import SessionState


@pytest.fixture
def bank_route() -> BankRoute:
    return BankRoute(country_code="de", bank_code="50030000")


def test_bank_route_normalizes_country(bank_route: BankRoute) -> None:
    assert bank_route.country_code == "DE"
    assert bank_route.bank_code == "50030000"
    assert bank_route.as_tuple() == ("DE", "50030000")
    assert str(bank_route) == "DE-50030000"


def test_bank_capabilities_support_lookup() -> None:
    capabilities = BankCapabilities(
        supported_operations=frozenset({"GET_BALANCE", "GET_TRANSACTIONS"}),
        supported_formats={"GET_TRANSACTIONS": ("camt.052",)},
    )
    assert capabilities.supports("GET_BALANCE")
    assert not capabilities.supports("GET_HOLDINGS")


def test_account_support_helpers(bank_route: BankRoute) -> None:
    caps = AccountCapabilities(
        can_fetch_balance=True,
        can_list_transactions=True,
        can_fetch_holdings=True,
        can_fetch_scheduled_debits=False,
    )
    account = Account(
        account_id="123:0",
        iban="DE001234",
        bic="BYLADEMMXXX",
        currency="EUR",
        product_name="Checking",
        owner=AccountOwner(name="Alice"),
        bank_route=bank_route,
        capabilities=caps,
        raw_labels=("Primary",),
        metadata={"account_number": "123"},
    )
    assert account.supports_transactions()
    assert account.supports_holdings()
    assert caps.as_dict()["transactions"] is True


def test_balance_snapshot_records_all_amounts() -> None:
    booked = BalanceAmount(amount=Decimal("123.45"), currency="EUR")
    pending = BalanceAmount(amount=Decimal("-10.00"), currency="EUR")
    available = BalanceAmount(amount=Decimal("111.00"), currency="EUR")
    credit_limit = BalanceAmount(amount=Decimal("5000.00"), currency="EUR")
    snapshot = BalanceSnapshot(
        account_id="acct",
        as_of=datetime(2024, 1, 1, tzinfo=UTC),
        booked=booked,
        pending=pending,
        available=available,
        credit_limit=credit_limit,
    )
    assert snapshot.booked.amount == Decimal("123.45")
    assert snapshot.pending.amount == Decimal("-10.00")
    assert snapshot.available.amount == Decimal("111.00")
    assert snapshot.credit_limit.amount == Decimal("5000.00")


def test_transaction_feed_preserves_entry_bounds() -> None:
    entries = (
        TransactionEntry(
            entry_id="1",
            booking_date=date(2024, 1, 2),
            value_date=date(2024, 1, 1),
            amount=Decimal("10.00"),
            currency="EUR",
            purpose="Test",
        ),
        TransactionEntry(
            entry_id="2",
            booking_date=date(2024, 1, 3),
            value_date=date(2024, 1, 2),
            amount=Decimal("-2.50"),
            currency="EUR",
            purpose="Debit",
        ),
    )
    feed = TransactionFeed(
        account_id="acct",
        entries=entries,
        start_date=date(2024, 1, 2),
        end_date=date(2024, 1, 3),
        has_more=True,
    )
    assert feed.entries[0].purpose == "Test"
    assert feed.has_more is True


def test_session_state_serialization_roundtrip(bank_route: BankRoute) -> None:
    created = datetime(2024, 5, 1, tzinfo=UTC)
    state = SessionState(
        route=bank_route,
        user_id="user",
        system_id="SYS",
        client_blob=b"\x01\x02",
        bpd_version=1,
        upd_version=None,
        created_at=created,
        version="1",
    )
    data = state.to_dict()
    restored = SessionState.from_dict(data)
    assert restored.route == bank_route
    assert restored.user_id == "user"
    assert restored.client_blob == b"\x01\x02"
    assert restored.created_at == created


def test_session_state_mask_hides_blob(bank_route: BankRoute) -> None:
    state = SessionState(
        route=bank_route,
        user_id="user",
        system_id="SYS",
        client_blob=b"secret",
    )
    masked = state.mask()
    assert masked["client_blob"] == "<6 bytes>"
    assert masked["route"]["country_code"] == "DE"
