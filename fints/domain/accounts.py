"""Domain representations for accounts and owners."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence

from .bank import BankRoute


@dataclass(frozen=True)
class AccountOwner:
    name: str
    address: Optional[str] = None


@dataclass(frozen=True)
class AccountCapabilities:
    can_fetch_balance: bool = False
    can_list_transactions: bool = False
    can_fetch_statements: bool = False
    can_fetch_holdings: bool = False
    can_fetch_scheduled_debits: bool = False

    def as_dict(self) -> Mapping[str, bool]:
        return {
            "balance": self.can_fetch_balance,
            "transactions": self.can_list_transactions,
            "statements": self.can_fetch_statements,
            "holdings": self.can_fetch_holdings,
            "scheduled_debits": self.can_fetch_scheduled_debits,
        }


@dataclass(frozen=True)
class Account:
    """Canonical description of an account we can read from."""

    account_id: str
    iban: Optional[str]
    bic: Optional[str]
    currency: Optional[str]
    product_name: Optional[str]
    owner: Optional[AccountOwner]
    bank_route: BankRoute
    capabilities: AccountCapabilities = field(default_factory=AccountCapabilities)
    raw_labels: Sequence[str] = field(default_factory=tuple)
    metadata: Mapping[str, str] = field(default_factory=dict)

    def supports_transactions(self) -> bool:
        return self.capabilities.can_list_transactions

    def supports_statements(self) -> bool:
        return self.capabilities.can_fetch_statements

    def supports_holdings(self) -> bool:
        return self.capabilities.can_fetch_holdings
