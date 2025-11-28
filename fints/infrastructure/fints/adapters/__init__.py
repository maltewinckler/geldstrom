"""Domain port implementations for FinTS 3.0 protocol.

These adapters implement the domain ports using the FinTS 3.0 protocol.

The adapters now support two modes via the USE_NEW_INFRASTRUCTURE flag:
- Legacy mode (default): Uses FinTS3PinTanClient
- New mode: Uses dialog/operations modules directly

Set USE_NEW_INFRASTRUCTURE = True in the adapter modules to enable the
new infrastructure. This is a transitional architecture - once the new
infrastructure is fully validated, the legacy code will be removed.
"""
from __future__ import annotations

from .accounts import FinTSAccountDiscovery
from .balances import FinTSBalanceAdapter
from .connection import ConnectionContext, FinTSConnectionHelper
from .session import FinTSSessionAdapter
from .statements import FinTSStatementAdapter
from .transactions import FinTSTransactionHistory

__all__ = [
    "ConnectionContext",
    "FinTSAccountDiscovery",
    "FinTSBalanceAdapter",
    "FinTSConnectionHelper",
    "FinTSSessionAdapter",
    "FinTSStatementAdapter",
    "FinTSTransactionHistory",
]

