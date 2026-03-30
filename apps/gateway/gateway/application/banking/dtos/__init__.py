"""Result DTOs for the banking bounded context."""

from .fetch_transactions import TransactionsResultEnvelope
from .get_balances import BalancesResultEnvelope
from .get_operation_status import OperationStatusEnvelope
from .get_tan_methods import TanMethodsResultEnvelope
from .list_accounts import ListAccountsResultEnvelope
from .resume_pending_operations import ResumeSummary

__all__ = [
    "BalancesResultEnvelope",
    "ListAccountsResultEnvelope",
    "OperationStatusEnvelope",
    "ResumeSummary",
    "TanMethodsResultEnvelope",
    "TransactionsResultEnvelope",
]
