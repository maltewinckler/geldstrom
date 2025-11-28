"""Domain port implementations for FinTS 3.0 protocol.

These adapters implement the domain ports using the FinTS 3.0 protocol,
delegating to the legacy client internally while exposing clean interfaces.
"""
from __future__ import annotations

from .accounts import FinTSAccountDiscovery
from .balances import FinTSBalanceAdapter
from .session import FinTSSessionAdapter
from .statements import FinTSStatementAdapter
from .transactions import FinTSTransactionHistory

__all__ = [
    "FinTSAccountDiscovery",
    "FinTSBalanceAdapter",
    "FinTSSessionAdapter",
    "FinTSStatementAdapter",
    "FinTSTransactionHistory",
]

