"""FinTS business operations using the new infrastructure.

This module contains operation implementations that work directly with
the Dialog and Protocol modules, without depending on the legacy client.

Operations are FinTS-specific and return FinTS-specific types. The adapters
layer is responsible for converting these to domain models.
"""
from .accounts import AccountInfo, AccountOperations
from .balances import BalanceOperations, BalanceResult, MT940Balance
from .enums import FinTSOperations
from .helpers import find_highest_supported_version
from .pagination import PaginatedResult, TouchdownPaginator
from .statements import StatementDocument, StatementInfo, StatementOperations
from .transactions import (
    CAMTTransactionResult,
    MT940TransactionResult,
    TransactionOperations,
)

__all__ = [
    # Enums
    "FinTSOperations",
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

