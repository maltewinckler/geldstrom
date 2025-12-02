"""Domain representations for accounts and owners."""
from __future__ import annotations

from typing import Mapping, Sequence

from pydantic import BaseModel

from .bank import BankRoute


class AccountOwner(BaseModel, frozen=True):
    name: str
    address: str | None = None


class AccountCapabilities(BaseModel, frozen=True):
    can_fetch_balance: bool = False
    can_list_transactions: bool = False
    can_fetch_holdings: bool = False
    can_fetch_scheduled_debits: bool = False

    def as_dict(self) -> Mapping[str, bool]:
        return {
            "balance": self.can_fetch_balance,
            "transactions": self.can_list_transactions,
            "holdings": self.can_fetch_holdings,
            "scheduled_debits": self.can_fetch_scheduled_debits,
        }


class Account(BaseModel, frozen=True):
    """Canonical description of an account we can read from."""

    account_id: str
    iban: str | None = None
    bic: str | None = None
    currency: str | None = None
    product_name: str | None = None
    owner: AccountOwner | None = None
    bank_route: BankRoute
    capabilities: AccountCapabilities = AccountCapabilities()
    raw_labels: Sequence[str] = ()
    metadata: Mapping[str, str] = {}

    def supports_transactions(self) -> bool:
        return self.capabilities.can_list_transactions

    def supports_holdings(self) -> bool:
        return self.capabilities.can_fetch_holdings
