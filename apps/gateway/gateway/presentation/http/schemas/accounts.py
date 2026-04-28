"""Accounts endpoint schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from gateway.presentation.http.schemas.bank_access import BankAccessRequest


class ListAccountsRequest(BankAccessRequest):
    pass


class AccountsCompletedResponse(BaseModel):
    model_config = {"extra": "forbid"}

    status: str
    operation_type: str = "accounts"
    accounts: list[dict[str, Any]]


class AccountsPendingResponse(BaseModel):
    model_config = {"extra": "forbid"}

    status: str
    operation_type: str = "accounts"
    operation_id: str
    expires_at: datetime
    polling_interval_seconds: int = 5
