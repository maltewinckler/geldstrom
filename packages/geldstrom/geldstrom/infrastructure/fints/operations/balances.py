"""Balance query operations for FinTS (HKSAL segments)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, time
from decimal import Decimal
from typing import TYPE_CHECKING

from geldstrom.infrastructure.fints.protocol import HKSAL5, HKSAL6, HKSAL7
from geldstrom.infrastructure.fints.protocol.formals import SEPAAccount

from .helpers import build_account_field, find_highest_supported_version

if TYPE_CHECKING:
    from geldstrom.infrastructure.fints.dialog import Dialog
    from geldstrom.infrastructure.fints.protocol import ParameterStore

logger = logging.getLogger(__name__)

# Supported HKSAL versions, newest first
SUPPORTED_HKSAL = (HKSAL7, HKSAL6, HKSAL5)


@dataclass
class MT940Balance:
    """Balance in MT940-compatible format."""

    amount: Decimal
    currency: str
    date: date
    status: str = "C"  # Credit (positive) or D (Debit/negative)

    @property
    def is_credit(self) -> bool:
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


class BalanceOperations:
    """Handles account balance queries via HKSAL segments."""

    def __init__(
        self,
        dialog: Dialog,
        parameters: ParameterStore,
    ) -> None:
        self._dialog = dialog
        self._parameters = parameters

    def fetch_balance(self, account: SEPAAccount) -> BalanceResult:
        logger.info(
            "Fetching balance for account %s", account.iban or account.accountnumber
        )

        hksal_class = find_highest_supported_version(
            self._parameters.bpd.segments,
            SUPPORTED_HKSAL,
            raise_if_missing="Bank does not support balance queries (HKSAL)",
        )
        segment = hksal_class(
            account=build_account_field(hksal_class, account),
            all_accounts=False,
        )
        response = self._dialog.send(segment)
        return self._extract_balance(response, segment)

    def _extract_balance(self, response, request_segment) -> BalanceResult:
        if response.raw_response is None:
            raise ValueError("No response received for balance query")
        for seg in response.raw_response.response_segments(request_segment, "HISAL"):
            booked = self._balance_to_mt940(seg.balance_booked)
            pending_balance = getattr(seg, "balance_pending", None)
            pending = None
            if pending_balance:
                pending = self._balance_to_mt940(pending_balance)
            available_amt = getattr(seg, "available_amount", None)
            available = available_amt.amount if available_amt else None
            credit_amt = getattr(seg, "line_of_credit", None)
            credit_line = credit_amt.amount if credit_amt else None
            booking_ts = getattr(seg, "booking_timestamp", None)
            if booking_ts:
                booking_date = booking_ts.date
                booking_time = booking_ts.time
            else:
                booking_date = getattr(seg, "booking_date", None)
                booking_time = getattr(seg, "booking_time", None)
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
        if balance_field is None:
            return None
        if getattr(balance_field, "credit_debit", None) is None:
            return None
        if hasattr(balance_field, "as_mt940_Balance"):
            try:
                mt940 = balance_field.as_mt940_Balance()
                return MT940Balance(
                    amount=mt940.amount.amount,
                    currency=mt940.amount.currency,
                    date=mt940.date,
                    status=mt940.status,
                )
            except (AttributeError, TypeError):
                pass
        amount_field = balance_field.amount
        if hasattr(amount_field, "amount"):
            amount_value = amount_field.amount
            currency = amount_field.currency
        else:
            amount_value = Decimal(str(amount_field))
            currency = "EUR"

        balance_date = getattr(balance_field, "date", None) or date.today()
        status = "C" if amount_value >= 0 else "D"

        return MT940Balance(
            amount=abs(amount_value),
            currency=currency,
            date=balance_date,
            status=status,
        )
