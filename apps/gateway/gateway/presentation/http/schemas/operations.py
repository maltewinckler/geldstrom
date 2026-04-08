"""Operation status endpoint schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, SecretStr


class OperationStatusResponse(BaseModel):
    model_config = {"extra": "forbid"}

    status: str
    operation_id: str
    result_payload: dict[str, Any] | None = None
    failure_reason: str | None = None
    expires_at: datetime | None = None
    polling_interval_seconds: int | None = None


class PollOperationRequest(BaseModel):
    """Credentials required to poll a pending operation's TAN status."""

    model_config = {"extra": "forbid"}

    protocol: Literal["fints"]
    blz: str = Field(min_length=8, max_length=8, pattern=r"^\d{8}$")
    user_id: str = Field(max_length=64)
    password: SecretStr
    tan_method: str | None = Field(default=None, max_length=64)
    tan_medium: str | None = Field(default=None, max_length=64)
