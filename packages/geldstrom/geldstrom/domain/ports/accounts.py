"""Port describing account discovery capabilities."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from geldstrom.domain import Account, BankCapabilities, SessionToken


class AccountDiscoveryPort(Protocol):
    """Retrieve account lists and bank capability metadata."""

    def fetch_bank_capabilities(self, state: SessionToken) -> BankCapabilities:
        raise NotImplementedError

    def fetch_accounts(self, state: SessionToken) -> Sequence[Account]:
        raise NotImplementedError
