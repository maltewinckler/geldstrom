"""Balance query operations for FinTS.

This module handles HKSAL segment exchanges for fetching account balances.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, time
from decimal import Decimal
from typing import TYPE_CHECKING, Sequence

from fints.exceptions import FinTSUnsupportedOperation
from fints.models import SEPAAccount
from fints.segments.saldo import HISAL5, HISAL6, HISAL7, HKSAL5, HKSAL6, HKSAL7

from .pagination import find_highest_supported_version

if TYPE_CHECKING:
    from fints.infrastructure.fints.dialog import Dialog
    from fints.infrastructure.fints.protocol import ParameterStore

logger = logging.getLogger(__name__)


@dataclass
class MT940Balance:
    """
    Balance information in MT940-compatible format.

    This mirrors the mt940.models.Balance structure for compatibility.
    """

    amount: Decimal
    currency: str
    date: date
    status: str = "C"  # Credit (positive) or D (Debit/negative)

    @property
    def is_credit(self) -> bool:
        """Return True if balance is positive (credit)."""
        return self.status == "C"


@dataclass
class BalanceResult:
    """Result of a balance query."""

    booked: MT940Balance
    pending: MT940Balance | None = None
    available: Decimal | None = None
    credit_line: Decimal | None = None
    booking_date: date | None = None
    booking_time: time | None = None


# Supported HKSAL versions, newest first
SUPPORTED_HKSAL = (HKSAL7, HKSAL6, HKSAL5)
SUPPORTED_HISAL = {
    7: HISAL7,
    6: HISAL6,
    5: HISAL5,
}


class BalanceOperations:
    """
    Handles balance query operations.

    This class provides methods to fetch account balances via HKSAL.

    Usage:
        ops = BalanceOperations(dialog, parameters)
        balance = ops.fetch_balance(account)
    """

    def __init__(
        self,
        dialog: "Dialog",
        parameters: "ParameterStore",
    ) -> None:
        """
        Initialize balance operations.

        Args:
            dialog: Active dialog for sending requests
            parameters: Parameter store with BPD
        """
        self._dialog = dialog
        self._parameters = parameters

    def fetch_balance(self, account: SEPAAccount) -> BalanceResult:
        """
        Fetch the current balance for an account.

        Args:
            account: SEPA account to query

        Returns:
            BalanceResult with booked and pending balances

        Raises:
            FinTSUnsupportedOperation: If bank doesn't support balance queries
        """
        logger.info("Fetching balance for account %s", account.iban or account.accountnumber)

        # Find highest supported HKSAL version
        hksal_class = find_highest_supported_version(
            self._parameters.bpd.segments,
            SUPPORTED_HKSAL,
        )

        if not hksal_class:
            raise FinTSUnsupportedOperation(
                "Bank does not support balance queries (HKSAL)"
            )

        # Build account field based on version
        account_type = hksal_class._fields["account"].type
        account_field = account_type.from_sepa_account(account)

        # Send HKSAL request
        segment = hksal_class(
            account=account_field,
            all_accounts=False,
        )
        response = self._dialog.send(segment)

        # Extract balance from HISAL response
        return self._extract_balance(response, segment, hksal_class.VERSION)

    def _extract_balance(
        self,
        response,
        request_segment,
        version: int,
    ) -> BalanceResult:
        """Extract balance from HISAL response segment."""
        if response.raw_response is None:
            raise ValueError("No response received for balance query")

        hisal_class = SUPPORTED_HISAL.get(version)
        if not hisal_class:
            # Fall back to generic segment search
            hisal_type = "HISAL"
        else:
            hisal_type = hisal_class

        for seg in response.raw_response.response_segments(request_segment, hisal_type):
            # Convert balance to MT940-compatible format
            booked = self._balance_to_mt940(seg.balance_booked)

            pending = None
            if hasattr(seg, "balance_pending") and seg.balance_pending:
                pending = self._balance_to_mt940(seg.balance_pending)

            available = None
            if hasattr(seg, "available_amount") and seg.available_amount:
                available = seg.available_amount.amount

            credit_line = None
            if hasattr(seg, "line_of_credit") and seg.line_of_credit:
                credit_line = seg.line_of_credit.amount

            booking_date = None
            booking_time = None
            if hasattr(seg, "booking_date"):
                booking_date = seg.booking_date
            if hasattr(seg, "booking_time"):
                booking_time = seg.booking_time
            if hasattr(seg, "booking_timestamp") and seg.booking_timestamp:
                booking_date = seg.booking_timestamp.date
                booking_time = seg.booking_timestamp.time

            return BalanceResult(
                booked=booked,
                pending=pending,
                available=available,
                credit_line=credit_line,
                booking_date=booking_date,
                booking_time=booking_time,
            )

        raise ValueError("No HISAL response segment found")

    def _balance_to_mt940(self, balance_field) -> MT940Balance | None:
        """Convert FinTS balance field to MT940Balance."""
        if balance_field is None:
            return None

        # Handle different balance field formats
        if hasattr(balance_field, "as_mt940_Balance"):
            # Check if credit_debit is set (required for conversion)
            if hasattr(balance_field, "credit_debit") and balance_field.credit_debit is None:
                return None
            try:
                mt940 = balance_field.as_mt940_Balance()
                return MT940Balance(
                    amount=mt940.amount.amount,
                    currency=mt940.amount.currency,
                    date=mt940.date,
                    status=mt940.status,
                )
            except (AttributeError, TypeError):
                return None

        # Manual extraction for Balance1/Balance2 types
        amount = balance_field.amount
        if hasattr(amount, "amount"):
            amount_value = amount.amount
            currency = amount.currency
        else:
            amount_value = amount
            currency = "EUR"

        balance_date = balance_field.date if hasattr(balance_field, "date") else date.today()
        status = "C" if amount_value >= 0 else "D"

        return MT940Balance(
            amount=abs(amount_value) if isinstance(amount_value, Decimal) else Decimal(str(amount_value)),
            currency=currency,
            date=balance_date,
            status=status,
        )

