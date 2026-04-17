"""Transactions endpoint schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel

from gateway.presentation.http.schemas.bank_access import BankAccessRequest


class FetchTransactionsRequest(BankAccessRequest):
    iban: str
    start_date: date | None = None
    end_date: date | None = None


class TransactionsCompletedResponse(BaseModel):
    model_config = {"extra": "forbid"}

    status: str
    operation_type: str = "transactions"
    transactions: list[dict[str, Any]]


class TransactionsPendingResponse(BaseModel):
    model_config = {"extra": "forbid"}

    status: str
    operation_type: str = "transactions"
    operation_id: str
    expires_at: datetime
    polling_interval_seconds: int = 5
