"""Transactions endpoint schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field, SecretStr


class FetchTransactionsRequest(BaseModel):
    model_config = {"extra": "forbid"}

    protocol: str
    blz: str
    user_id: str = Field(max_length=64)
    password: SecretStr
    iban: str
    start_date: date | None = None
    end_date: date | None = None
    tan_method: str | None = Field(default=None, max_length=64)
    tan_medium: str | None = Field(default=None, max_length=64)


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
