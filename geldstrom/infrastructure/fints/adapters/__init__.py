"""Domain port implementations for FinTS 3.0 protocol.

These adapters implement the domain ports using the FinTS 3.0 protocol.
They use the new dialog/operations infrastructure for all bank communication.
"""
from __future__ import annotations

from .accounts import FinTSAccountDiscovery
from .balances import FinTSBalanceAdapter
from .connection import ConnectionContext, FinTSConnectionHelper
from .helpers import account_key, locate_sepa_account
from .serialization import compress_datablob, decompress_datablob
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
    "account_key",
    "compress_datablob",
    "decompress_datablob",
    "locate_sepa_account",
]
