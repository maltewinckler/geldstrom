"""Tests for the balances operations module."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from geldstrom.infrastructure.fints.operations.balances import (
    BalanceOperations,
    BalanceResult,
    MT940Balance,
)


class TestMT940Balance:
    """Tests for MT940Balance dataclass."""

    def test_credit_balance(self):
        """MT940Balance should correctly identify credit balances."""
        balance = MT940Balance(
            amount=Decimal("1234.56"),
            currency="EUR",
            date=date(2024, 1, 15),
            status="C",
        )

        assert balance.amount == Decimal("1234.56")
        assert balance.is_credit is True

    def test_debit_balance(self):
        """MT940Balance should correctly identify debit balances."""
        balance = MT940Balance(
            amount=Decimal("500.00"),
            currency="EUR",
            date=date(2024, 1, 15),
            status="D",
        )

        assert balance.is_credit is False


class TestBalanceResult:
    """Tests for BalanceResult dataclass."""

    def test_basic_result(self):
        """BalanceResult should store booked balance."""
        booked = MT940Balance(
            amount=Decimal("1000.00"),
            currency="EUR",
            date=date(2024, 1, 15),
        )
        result = BalanceResult(booked=booked)

        assert result.booked.amount == Decimal("1000.00")
        assert result.pending is None
        assert result.available is None

    def test_full_result(self):
        """BalanceResult should store all optional fields."""
        booked = MT940Balance(
            amount=Decimal("1000.00"),
            currency="EUR",
            date=date(2024, 1, 15),
        )
        pending = MT940Balance(
            amount=Decimal("50.00"),
            currency="EUR",
            date=date(2024, 1, 15),
        )

        result = BalanceResult(
            booked=booked,
            pending=pending,
            available=Decimal("950.00"),
            credit_line=Decimal("5000.00"),
            booking_date=date(2024, 1, 15),
        )

        assert result.pending is not None
        assert result.available == Decimal("950.00")
        assert result.credit_line == Decimal("5000.00")


class TestBalanceOperations:
    """Tests for BalanceOperations class."""

    @pytest.fixture
    def mock_dialog(self):
        """Create a mock dialog."""
        return MagicMock()

    @pytest.fixture
    def mock_parameters(self):
        """Create a mock parameter store with HKSAL support."""
        params = MagicMock()
        # Mock BPD that supports HKSAL7
        mock_segment = MagicMock()
        mock_segment.header.version = 7
        params.bpd.segments.find_segment_highest_version.return_value = mock_segment
        return params

    def test_raises_if_unsupported(self, mock_dialog, mock_parameters):
        """fetch_balance should raise if bank doesn't support HKSAL."""
        from geldstrom.exceptions import FinTSUnsupportedOperation
        from geldstrom.infrastructure.fints.protocol.formals import SEPAAccount

        # Mock BPD that doesn't support HKSAL
        mock_parameters.bpd.segments.find_segment_highest_version.return_value = None

        account = SEPAAccount(
            iban="DE89370400440532013000",
            bic="COBADEFFXXX",
            accountnumber="123456",
            subaccount="0",
            blz="37040044",
        )

        ops = BalanceOperations(mock_dialog, mock_parameters)

        with pytest.raises(FinTSUnsupportedOperation):
            ops.fetch_balance(account)

