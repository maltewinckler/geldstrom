"""Result DTOs for the banking bounded context."""

from gateway.application.banking.dtos.fetch_transactions import (
    TransactionsResultEnvelope,
)
from gateway.application.banking.dtos.get_balances import BalancesResultEnvelope
from gateway.application.banking.dtos.get_operation_status import (
    OperationStatusEnvelope,
)
from gateway.application.banking.dtos.get_tan_methods import TanMethodsResultEnvelope
from gateway.application.banking.dtos.list_accounts import ListAccountsResultEnvelope
from gateway.application.banking.dtos.lookup_bank import BankInfoEnvelope

__all__ = [
    "BankInfoEnvelope",
    "BalancesResultEnvelope",
    "ListAccountsResultEnvelope",
    "OperationStatusEnvelope",
    "TanMethodsResultEnvelope",
    "TransactionsResultEnvelope",
]
