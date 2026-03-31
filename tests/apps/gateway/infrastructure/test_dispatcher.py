"""Tests for banking connector protocol dispatch."""

import asyncio
from datetime import date
from unittest.mock import AsyncMock

from gateway.domain.banking_gateway import (
    AccountsResult,
    BankingConnector,
    OperationStatus,
)
from gateway.infrastructure.banking.protocols import BankingConnectorDispatcher


def test_dispatcher_delegates_to_fints_connector() -> None:
    inner = AsyncMock(spec=BankingConnector)
    inner.list_accounts.return_value = AccountsResult(
        status=OperationStatus.COMPLETED, accounts=[]
    )
    dispatcher = BankingConnectorDispatcher(fints_connector=inner)

    result = asyncio.run(
        dispatcher.list_accounts(
            institute=AsyncMock(), credentials=AsyncMock()
        )
    )

    assert result.status is OperationStatus.COMPLETED
    inner.list_accounts.assert_called_once()
