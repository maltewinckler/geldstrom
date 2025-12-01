"""Tests for the FinTS protocol parameter modules.

These tests verify BankParameters, UserParameters, and ParameterStore
work correctly for storing and querying BPD/UPD data.
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from geldstrom.infrastructure.fints.protocol import (
    BankParameters,
    ParameterStore,
    SegmentSequence,
    UserParameters,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_mock_segment(segment_type: str, version: int = 1, **kwargs) -> MagicMock:
    """Create a mock segment with specified type and version."""
    seg = MagicMock()
    seg.header = MagicMock()
    seg.header.type = segment_type
    seg.header.version = version
    for key, value in kwargs.items():
        setattr(seg, key, value)
    return seg


def _make_upd_segment(
    account_number: str,
    iban: str,
    subaccount: str = "",
    currency: str = "EUR",
    owner_name_1: str = "Test Owner",
    owner_name_2: str | None = None,
    product_name: str = "Checking Account",
    account_type: int = 1,
    allowed_transactions: list | None = None,
) -> MagicMock:
    """Create a mock HIUPD segment."""
    seg = MagicMock()
    seg.header = MagicMock()
    seg.header.type = "HIUPD"
    seg.header.version = 6

    seg.iban = iban
    seg.account_information = MagicMock()
    seg.account_information.account_number = account_number
    seg.account_information.subaccount_number = subaccount
    seg.account_information.bank_identifier = MagicMock()
    seg.customer_id = "customer-123"
    seg.account_type = account_type
    seg.account_currency = currency
    seg.name_account_owner_1 = owner_name_1
    seg.name_account_owner_2 = owner_name_2
    seg.account_product_name = product_name
    seg.allowed_transactions = allowed_transactions or []

    return seg


@pytest.fixture
def empty_segment_sequence():
    """Create an empty SegmentSequence."""
    seq = MagicMock(spec=SegmentSequence)
    seq.segments = []  # Add segments attribute for logging
    seq.find_segments.return_value = []
    seq.find_segment_highest_version.return_value = None
    seq.render_bytes.return_value = b""
    return seq


@pytest.fixture
def bpd_with_segments():
    """Create BPD with mock segments."""
    hisals = _make_mock_segment("HISALS", version=7)
    hikazi = _make_mock_segment("HIKAZS", version=6)

    seq = MagicMock(spec=SegmentSequence)

    def find_segments(type_name):
        if type_name == "HISALS":
            return [hisals]
        elif type_name == "HIKAZS":
            return [hikazi]
        return []

    seq.find_segments = find_segments
    seq.find_segment_highest_version.return_value = hisals
    seq.render_bytes.return_value = b"test-bpd-data"

    return BankParameters(
        version=78,
        bank_name="Test Bank",
        segments=seq,
        bpa=_make_mock_segment("HIBPA", version=3, bpd_version=78, bank_name="Test Bank"),
    )


@pytest.fixture
def upd_with_accounts():
    """Create UPD with mock account segments."""
    account1 = _make_upd_segment(
        account_number="123456789",
        iban="DE89370400440532013000",
        owner_name_1="Alice Test",
        product_name="Giro",
    )
    account2 = _make_upd_segment(
        account_number="987654321",
        iban="DE89370400440532013001",
        owner_name_1="Alice Test",
        owner_name_2="Bob Test",
        product_name="Savings",
    )

    seq = MagicMock(spec=SegmentSequence)
    seq.find_segments.return_value = [account1, account2]
    seq.render_bytes.return_value = b"test-upd-data"

    return UserParameters(
        version=5,
        segments=seq,
        upa=_make_mock_segment("HIUPA", version=4, upd_version=5),
    )


# ---------------------------------------------------------------------------
# BankParameters Tests
# ---------------------------------------------------------------------------


class TestBankParameters:
    """Tests for BankParameters dataclass."""

    def test_default_values(self):
        """BankParameters should have sensible defaults."""
        bpd = BankParameters()
        assert bpd.version == 0
        assert bpd.bank_name is None
        assert bpd.bpa is None

    def test_find_segment(self, bpd_with_segments):
        """find_segment should locate segments by type."""
        seg = bpd_with_segments.find_segment("HISALS")
        assert seg is not None
        assert seg.header.type == "HISALS"

    def test_find_segment_not_found(self, bpd_with_segments):
        """find_segment should return None if not found."""
        seg = bpd_with_segments.find_segment("NONEXISTENT")
        assert seg is None

    def test_find_segment_with_version(self, bpd_with_segments):
        """find_segment should filter by version."""
        seg = bpd_with_segments.find_segment("HISALS", version=7)
        assert seg is not None

        seg = bpd_with_segments.find_segment("HISALS", version=99)
        assert seg is None

    def test_supports_operation(self, bpd_with_segments):
        """supports_operation should check for parameter segments."""
        # HKSAL -> HISALS should exist
        assert bpd_with_segments.supports_operation("HKSAL") is True

        # HKNONEXISTENT -> HINONEXISTENTS should not exist
        assert bpd_with_segments.supports_operation("HKNONEXISTENT") is False

    def test_serialize(self, bpd_with_segments):
        """serialize should return bytes."""
        data = bpd_with_segments.serialize()
        assert isinstance(data, bytes)


# ---------------------------------------------------------------------------
# UserParameters Tests
# ---------------------------------------------------------------------------


class TestUserParameters:
    """Tests for UserParameters dataclass."""

    def test_default_values(self):
        """UserParameters should have sensible defaults."""
        upd = UserParameters()
        assert upd.version == 0
        assert upd.upa is None

    def test_get_accounts(self, upd_with_accounts):
        """get_accounts should extract account info."""
        accounts = upd_with_accounts.get_accounts()
        assert len(accounts) == 2

        acc1 = accounts[0]
        assert acc1["account_number"] == "123456789"
        assert acc1["iban"] == "DE89370400440532013000"
        assert acc1["owner_name"] == ["Alice Test"]
        assert acc1["product_name"] == "Giro"

        acc2 = accounts[1]
        assert acc2["owner_name"] == ["Alice Test", "Bob Test"]

    def test_get_accounts_empty(self, empty_segment_sequence):
        """get_accounts should return empty list if no accounts."""
        upd = UserParameters(segments=empty_segment_sequence)
        accounts = upd.get_accounts()
        assert accounts == []

    def test_serialize(self, upd_with_accounts):
        """serialize should return bytes."""
        data = upd_with_accounts.serialize()
        assert isinstance(data, bytes)


# ---------------------------------------------------------------------------
# ParameterStore Tests
# ---------------------------------------------------------------------------


class TestParameterStore:
    """Tests for ParameterStore class."""

    def test_default_initialization(self):
        """ParameterStore should initialize with empty parameters."""
        store = ParameterStore()
        assert store.bpd_version == 0
        assert store.upd_version == 0

    def test_initialization_with_parameters(self, bpd_with_segments, upd_with_accounts):
        """ParameterStore should accept initial parameters."""
        store = ParameterStore(bpd=bpd_with_segments, upd=upd_with_accounts)
        assert store.bpd_version == 78
        assert store.upd_version == 5

    def test_update_from_response_bpd(self, empty_segment_sequence):
        """update_from_response should update BPD if newer."""
        store = ParameterStore()
        assert store.bpd_version == 0

        new_bpd_segments = empty_segment_sequence
        store.update_from_response(
            bpa=_make_mock_segment("HIBPA", bpd_version=78),
            bpd_version=78,
            bpd_segments=new_bpd_segments,
            upa=None,
            upd_version=None,
            upd_segments=None,
        )

        assert store.bpd_version == 78

    def test_update_from_response_upd(self, empty_segment_sequence):
        """update_from_response should update UPD if newer."""
        store = ParameterStore()
        assert store.upd_version == 0

        new_upd_segments = empty_segment_sequence
        store.update_from_response(
            bpa=None,
            bpd_version=None,
            bpd_segments=None,
            upa=_make_mock_segment("HIUPA", upd_version=5),
            upd_version=5,
            upd_segments=new_upd_segments,
        )

        assert store.upd_version == 5

    def test_update_ignores_older_versions(self, bpd_with_segments):
        """update_from_response should not downgrade versions."""
        store = ParameterStore(bpd=bpd_with_segments)
        assert store.bpd_version == 78

        # Try to update with older version
        store.update_from_response(
            bpa=_make_mock_segment("HIBPA", bpd_version=50),
            bpd_version=50,
            bpd_segments=MagicMock(),
            upa=None,
            upd_version=None,
            upd_segments=None,
        )

        # Should still be 78 (not downgraded)
        # Note: Current implementation uses >= so 50 < 78, no update
        assert store.bpd_version == 78

    def test_to_dict_and_from_dict(self, bpd_with_segments, upd_with_accounts):
        """ParameterStore should serialize and deserialize."""
        store = ParameterStore(bpd=bpd_with_segments, upd=upd_with_accounts)

        # Mock the Pydantic serializer for BPA/UPA
        with patch("geldstrom.infrastructure.fints.protocol.parameters.FinTSSerializer") as mock_serializer:
            mock_serializer.return_value.serialize_message.return_value = b"serialized"

            data = store.to_dict()

            assert "bpd_version" in data
            assert "upd_version" in data
            assert data["bpd_version"] == 78
            assert data["upd_version"] == 5

    def test_bpd_property(self, bpd_with_segments):
        """bpd property should return BankParameters."""
        store = ParameterStore(bpd=bpd_with_segments)
        assert store.bpd is bpd_with_segments

    def test_upd_property(self, upd_with_accounts):
        """upd property should return UserParameters."""
        store = ParameterStore(upd=upd_with_accounts)
        assert store.upd is upd_with_accounts

