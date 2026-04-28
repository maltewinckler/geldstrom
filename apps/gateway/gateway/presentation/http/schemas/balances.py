"""Balances endpoint schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from gateway.presentation.http.schemas.bank_access import BankAccessRequest


class GetBalancesRequest(BankAccessRequest):
    pass


class BalancesCompletedResponse(BaseModel):
    model_config = {"extra": "forbid"}

    status: str
    operation_type: str = "balances"
    balances: list[dict[str, Any]]


class BalancesPendingResponse(BaseModel):
    model_config = {"extra": "forbid"}

    status: str
    operation_type: str = "balances"
    operation_id: str
    expires_at: datetime
    polling_interval_seconds: int = 5
