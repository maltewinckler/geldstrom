"""Shared helper functions for FinTS adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from geldstrom.infrastructure.fints.protocol.formals import SEPAAccount


def account_key(account: SEPAAccount) -> str:
    """Create lookup key from SEPA account."""
    return f"{account.accountnumber}:{account.subaccount or '0'}"


def locate_sepa_account(
    account_ops,
    account_id: str,
) -> SEPAAccount:
    """Find SEPA account by account ID."""
    for sepa in account_ops.fetch_sepa_accounts():
        if account_key(sepa) == account_id:
            return sepa
    raise ValueError(f"Account {account_id} not available from bank")


__all__ = ["account_key", "locate_sepa_account"]
