"""TAN methods endpoint schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, SecretStr


class GetTanMethodsRequest(BaseModel):
    model_config = {"extra": "forbid"}

    protocol: str
    blz: str
    user_id: str
    password: SecretStr


class TanMethodsCompletedResponse(BaseModel):
    model_config = {"extra": "forbid"}

    status: str
    methods: list[dict[str, Any]]


class TanMethodsPendingResponse(BaseModel):
    model_config = {"extra": "forbid"}

    status: str
    operation_id: str
    expires_at: datetime
    polling_interval_seconds: int = 5
