"""FinTS segment-level request/response handlers.

This package contains stateless operations that take an already-open
``Dialog`` and execute FinTS business segments (HKSAL, HKKAZ, HKCAZ,
HKSPA, etc.). They handle version negotiation, pagination, and
response parsing, returning FinTS-specific intermediate types.

The ``services`` layer is responsible for connection lifecycle
management and mapping these results to domain models.
"""

from .accounts import AccountInfo, AccountOperations
from .balances import BalanceOperations, BalanceResult, HisalBalance
from .enums import FinTSOperations
from .helpers import find_highest_supported_version
from .pagination import PaginatedResult, TouchdownPaginator
from .transactions import (
    CamtFetcher,
    Mt940Fetcher,
    mt940_to_array,
    parse_camt_approved_response,
    parse_mt940_approved_response,
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
    "HisalBalance",
    # Transactions
    "CamtFetcher",
    "Mt940Fetcher",
    "mt940_to_array",
    "parse_camt_approved_response",
    "parse_mt940_approved_response",
]
