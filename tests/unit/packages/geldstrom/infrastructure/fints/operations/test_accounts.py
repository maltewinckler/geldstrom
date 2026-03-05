"""Tests for the accounts operations module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from geldstrom.infrastructure.fints.exceptions import FinTSSCARequiredError
from geldstrom.infrastructure.fints.operations.accounts import (
    AccountInfo,
    AccountOperations,
)
from geldstrom.infrastructure.fints.protocol.formals import SEPAAccount


class TestAccountInfo:
    """Tests for AccountInfo dataclass."""

    def test_basic_account_info(self):
        """AccountInfo should store all fields."""
        info = AccountInfo(
            account_number="123456",
            subaccount_number="0",
            iban="DE89370400440532013000",
            bic="COBADEFFXXX",
            currency="EUR",
            owner_name=["John Doe"],
            product_name="Girokonto",
            account_type=1,
            bank_identifier=MagicMock(),
            allowed_operations=["HKSAL", "HKKAZ"],
        )

        assert info.account_number == "123456"
        assert info.iban == "DE89370400440532013000"
        assert info.bic == "COBADEFFXXX"
        assert info.owner_name == ["John Doe"]
        assert "HKSAL" in info.allowed_operations


class TestAccountOperations:
    """Tests for AccountOperations class."""

    @pytest.fixture
    def mock_dialog(self):
        """Create a mock dialog."""
        return MagicMock()

    @pytest.fixture
    def mock_parameters(self):
        """Create a mock parameter store."""
        params = MagicMock()
        params.upd.get_accounts.return_value = []
        return params

    def test_fetch_sepa_accounts_sends_hkspa(self, mock_dialog, mock_parameters):
        """fetch_sepa_accounts should send HKSPA1 segment."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.raw_response = MagicMock()
        mock_response.raw_response.find_segments.return_value = []
        # No SCA error
        mock_response.get_response_by_code.return_value = None
        mock_dialog.send.return_value = mock_response

        ops = AccountOperations(mock_dialog, mock_parameters)
        result = ops.fetch_sepa_accounts()

        # Verify HKSPA was sent
        mock_dialog.send.assert_called_once()
        sent_segment = mock_dialog.send.call_args[0][0]
        assert sent_segment.__class__.__name__ == "HKSPA1"

        assert result == []

    def test_fetch_sepa_accounts_extracts_from_hispa(
        self, mock_dialog, mock_parameters
    ):
        """fetch_sepa_accounts should extract accounts from HISPA response."""
        # Create mock SEPA account
        mock_sepa = SEPAAccount(
            iban="DE89370400440532013000",
            bic="COBADEFFXXX",
            accountnumber="123456",
            subaccount="0",
            blz="37040044",
        )

        # Create mock HISPA segment
        mock_hispa = MagicMock()
        mock_acc = MagicMock()
        mock_acc.as_sepa_account.return_value = mock_sepa
        mock_hispa.accounts = [mock_acc]

        mock_response = MagicMock()
        mock_response.raw_response = MagicMock()
        mock_response.raw_response.find_segments.return_value = [mock_hispa]
        # No SCA error
        mock_response.get_response_by_code.return_value = None
        mock_dialog.send.return_value = mock_response

        ops = AccountOperations(mock_dialog, mock_parameters)
        result = ops.fetch_sepa_accounts()

        assert len(result) == 1
        assert result[0].iban == "DE89370400440532013000"

    def test_get_accounts_from_upd(self, mock_dialog, mock_parameters):
        """get_accounts_from_upd should extract from cached UPD."""
        mock_parameters.upd.get_accounts.return_value = [
            {
                "account_number": "123456",
                "subaccount_number": "0",
                "iban": "DE89370400440532013000",
                "currency": "EUR",
                "owner_name": ["Alice"],
                "product_name": "Checking",
                "type": 1,
                "bank_identifier": MagicMock(),
                "allowed_transactions": [],
            }
        ]

        ops = AccountOperations(mock_dialog, mock_parameters)
        result = ops.get_accounts_from_upd()

        assert len(result) == 1
        assert result[0].account_number == "123456"
        assert result[0].owner_name == ["Alice"]

    def test_merge_sepa_info_adds_bic(self, mock_dialog, mock_parameters):
        """merge_sepa_info should add BIC from SEPA accounts."""
        upd_accounts = [
            AccountInfo(
                account_number="123456",
                subaccount_number="0",
                iban="DE89370400440532013000",
                bic=None,  # No BIC yet
                currency="EUR",
                owner_name=[],
                product_name=None,
                account_type=None,
                bank_identifier=None,
                allowed_operations=[],
            )
        ]

        sepa_accounts = [
            SEPAAccount(
                iban="DE89370400440532013000",
                bic="COBADEFFXXX",
                accountnumber="123456",
                subaccount="0",
                blz="37040044",
            )
        ]

        ops = AccountOperations(mock_dialog, mock_parameters)
        result = ops.merge_sepa_info(upd_accounts, sepa_accounts)

        assert len(result) == 1
        assert result[0].bic == "COBADEFFXXX"

    def test_fetch_sepa_accounts_raises_sca_error(self, mock_dialog, mock_parameters):
        """fetch_sepa_accounts should raise FinTSSCARequiredError on error 9075."""
        # Setup mock response with SCA error
        mock_response = MagicMock()
        mock_response.raw_response = MagicMock()
        mock_response.raw_response.find_segments.return_value = []

        # Simulate SCA required error (9075)
        sca_error = MagicMock()
        sca_error.text = "Starke Kundenauthentifizierung notwendig."
        mock_response.get_response_by_code.return_value = sca_error
        mock_dialog.send.return_value = mock_response

        ops = AccountOperations(mock_dialog, mock_parameters)

        with pytest.raises(FinTSSCARequiredError) as exc_info:
            ops.fetch_sepa_accounts()

        assert "tan_method" in str(exc_info.value)
        assert "2FA" in str(exc_info.value)
