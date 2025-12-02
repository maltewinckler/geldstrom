"""FinTS Amount and Balance DEGs.

These DEGs represent monetary amounts and account balances.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from mt940.models import Balance as MT940Balance
from pydantic import Field

from ..base import FinTSDataElementGroup
from ..types import FinTSAmount, FinTSCurrency, FinTSDate, FinTSTime
from .enums import CreditDebit


class Amount(FinTSDataElementGroup):
    """Betrag (Amount) - Version 1.

    Represents a monetary amount with currency.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle

    Example:
        amount = Amount(amount=Decimal("1234.56"), currency="EUR")
        amount = Amount.from_wire_list(["1234,56", "EUR"])
    """

    amount: FinTSAmount = Field(description="Wert (Value)")
    currency: FinTSCurrency = Field(description="Währung (Currency)")

    def __str__(self) -> str:
        return f"{self.amount} {self.currency}"


class Balance(FinTSDataElementGroup):
    """Saldo (Balance) - Version 2.

    Represents an account balance with credit/debit indicator, amount, and date.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle

    Example:
        balance = Balance(
            credit_debit=CreditDebit.CREDIT,
            amount=Amount(amount=Decimal("1234.56"), currency="EUR"),
            date=date(2023, 12, 25),
        )
    """

    credit_debit: CreditDebit = Field(description="Soll-Haben-Kennzeichen")
    amount: Amount = Field(description="Betrag")
    date: FinTSDate = Field(description="Datum")
    time: FinTSTime | None = Field(default=None, description="Uhrzeit")

    @property
    def signed_amount(self) -> Decimal:
        """Get the amount with sign based on credit/debit.

        Returns:
            Positive for credit, negative for debit.
        """
        if self.credit_debit == CreditDebit.CREDIT:
            return self.amount.amount
        return -self.amount.amount

    @property
    def value(self) -> Decimal:
        """Alias for signed_amount for backward compatibility."""
        return self.signed_amount

    @property
    def currency(self) -> str:
        """Get currency from nested amount."""
        return self.amount.currency

    def as_mt940_balance(self) -> MT940Balance:
        """Convert to mt940 Balance model.

        Returns:
            mt940.models.Balance instance
        """

        return MT940Balance(
            self.credit_debit.value,
            f"{self.amount.amount:.12f}".rstrip("0"),
            self.date,
            currency=self.amount.currency,
        )


class BalanceSimple(FinTSDataElementGroup):
    """Saldo (Balance) - Version 1 (simple format).

    Older balance format without nested Amount DEG.

    Source: HBCI Homebanking-Computer-Interface, Schnittstellenspezifikation
    """

    credit_debit: CreditDebit = Field(description="Soll-Haben-Kennzeichen")
    amount: FinTSAmount = Field(description="Wert")
    currency: FinTSCurrency = Field(description="Währung")
    date: FinTSDate = Field(description="Datum")
    time: FinTSTime | None = Field(default=None, description="Uhrzeit")

    @property
    def signed_amount(self) -> Decimal:
        """Get the amount with sign based on credit/debit."""
        if self.credit_debit == CreditDebit.CREDIT:
            return self.amount
        return -self.amount

    def as_mt940_balance(self) -> MT940Balance:
        """Convert to mt940 Balance model."""
        return MT940Balance(
            self.credit_debit.value,
            f"{self.amount:.12f}".rstrip("0"),
            self.date,
            currency=self.currency,
        )


class Timestamp(FinTSDataElementGroup):
    """Zeitstempel (Timestamp).

    Represents a date with optional time.

    Source: FinTS 3.0 Messages - Multibankfähige Geschäftsvorfälle
    """

    date: FinTSDate = Field(description="Datum")
    time: FinTSTime | None = Field(default=None, description="Uhrzeit")


# =============================================================================
# Simple Value Models (for internal use)
# =============================================================================


class Holding(FinTSDataElementGroup):
    """Securities holding representation.

    Represents a single holding in a depot/securities account.
    Used for parsing depot information from MT535 messages.
    """

    ISIN: str = Field(description="ISIN code")
    name: str = Field(description="Security name")
    market_value: Decimal | None = Field(
        default=None, description="Market value per unit"
    )
    value_symbol: str | None = Field(
        default=None, description="Currency/symbol for market value"
    )
    valuation_date: date | None = Field(default=None, description="Date of valuation")
    pieces: Decimal | None = Field(
        default=None, description="Number of pieces/units held"
    )
    total_value: Decimal | None = Field(
        default=None, description="Total value of holding"
    )
    acquisitionprice: Decimal | None = Field(
        default=None, description="Acquisition price per unit"
    )


__all__ = [
    "Amount",
    "Balance",
    "BalanceSimple",
    "Timestamp",
    "Holding",
]
