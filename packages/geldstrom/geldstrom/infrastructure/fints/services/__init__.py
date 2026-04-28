"""FinTS orchestration layer - connection lifecycle and domain mapping.

Each service manages the full FinTS connection lifecycle
(connect -> sync -> dialog -> business request -> close) and maps
the FinTS-specific results from ``operations`` into domain models.

Stack: services -> operations -> dialog -> protocol
"""

from __future__ import annotations

from .accounts import AccountDiscoveryResult, FinTSAccountService
from .balances import FinTSBalanceService
from .metadata import FinTSMetadataService
from .transactions import FinTSTransactionService

__all__ = [
    "AccountDiscoveryResult",
    "FinTSAccountService",
    "FinTSBalanceService",
    "FinTSMetadataService",
    "FinTSTransactionService",
]
