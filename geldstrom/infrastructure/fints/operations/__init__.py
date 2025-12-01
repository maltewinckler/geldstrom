"""FinTS business operations using the new infrastructure.

This module contains operation implementations that work directly with
the Dialog and Protocol modules, without depending on the legacy client.

Operations are FinTS-specific and return FinTS-specific types. The adapters
layer is responsible for converting these to domain models.
"""
from .accounts import AccountInfo, AccountOperations
from .balances import BalanceOperations, BalanceResult, MT940Balance
from .enums import FinTSOperations
from .pagination import PaginatedResult, TouchdownPaginator, find_highest_supported_version
from .statements import StatementDocument, StatementInfo, StatementOperations
from .system_id import SystemIdSynchronizer, ensure_system_id
from .transactions import (
    CAMTTransactionResult,
    MT940TransactionResult,
    TransactionOperations,
)

__all__ = [
    # Enums
    "FinTSOperations",
    # System ID
    "SystemIdSynchronizer",
    "ensure_system_id",
    # Pagination
    "PaginatedResult",
    "TouchdownPaginator",
    "find_highest_supported_version",
    # Accounts
    "AccountInfo",
    "AccountOperations",
    # Balances
    "BalanceOperations",
    "BalanceResult",
    "MT940Balance",
    # Transactions
    "CAMTTransactionResult",
    "MT940TransactionResult",
    "TransactionOperations",
    # Statements
    "StatementDocument",
    "StatementInfo",
    "StatementOperations",
]

