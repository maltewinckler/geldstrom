"""Operation status endpoint schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, SecretStr


class PollPendingResponse(BaseModel):
    model_config = {"extra": "forbid"}

    status: Literal["pending_confirmation"]
    operation_type: str
    operation_id: str
    expires_at: datetime
    polling_interval_seconds: int = 5


class PollCompletedAccountsResponse(BaseModel):
    model_config = {"extra": "forbid"}

    status: Literal["completed"]
    operation_type: Literal["accounts"]
    operation_id: str
    accounts: list[dict[str, Any]]


class PollCompletedTransactionsResponse(BaseModel):
    model_config = {"extra": "forbid"}

    status: Literal["completed"]
    operation_type: Literal["transactions"]
    operation_id: str
    transactions: list[dict[str, Any]]


class PollCompletedBalancesResponse(BaseModel):
    model_config = {"extra": "forbid"}

    status: Literal["completed"]
    operation_type: Literal["balances"]
    operation_id: str
    balances: list[dict[str, Any]]


class PollCompletedTanMethodsResponse(BaseModel):
    model_config = {"extra": "forbid"}

    status: Literal["completed"]
    operation_type: Literal["tan_methods"]
    operation_id: str
    methods: list[dict[str, Any]]


class PollFailedResponse(BaseModel):
    model_config = {"extra": "forbid"}

    status: Literal["failed", "expired"]
    operation_type: str
    operation_id: str
    failure_reason: str | None = None


class PollOperationRequest(BaseModel):
    """Credentials required to poll a pending operation's TAN status."""

    model_config = {"extra": "forbid"}

    protocol: Literal["fints"]
    blz: str = Field(min_length=8, max_length=8, pattern=r"^\d{8}$")
    user_id: str = Field(max_length=64)
    password: SecretStr
    tan_method: str | None = Field(default=None, max_length=64)
    tan_medium: str | None = Field(default=None, max_length=64)
