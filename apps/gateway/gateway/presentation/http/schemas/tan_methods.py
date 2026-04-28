"""TAN methods endpoint schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from gateway.presentation.http.schemas.bank_access import BankAccessRequest


class GetTanMethodsRequest(BankAccessRequest):
    pass


class TanMethodsCompletedResponse(BaseModel):
    model_config = {"extra": "forbid"}

    status: str
    operation_type: str = "tan_methods"
    methods: list[dict[str, Any]]


class TanMethodsPendingResponse(BaseModel):
    model_config = {"extra": "forbid"}

    status: str
    operation_type: str = "tan_methods"
    operation_id: str
    expires_at: datetime
    polling_interval_seconds: int = 5
