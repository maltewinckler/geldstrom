"""Transactions endpoint schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, SecretStr


class FetchTransactionsRequest(BaseModel):
    model_config = {"extra": "forbid"}

    protocol: str
    blz: str
    user_id: str
    password: SecretStr
    iban: str
    start_date: date | None = None
    end_date: date | None = None


class TransactionsCompletedResponse(BaseModel):
    model_config = {"extra": "forbid"}

    status: str
    transactions: list[dict[str, Any]]


class TransactionsPendingResponse(BaseModel):
    model_config = {"extra": "forbid"}

    status: str
    operation_id: str
    expires_at: datetime
    polling_interval_seconds: int = 5
