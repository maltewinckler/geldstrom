"""Operation status endpoint schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class OperationStatusResponse(BaseModel):
    model_config = {"extra": "forbid"}

    status: str
    operation_id: str
    result_payload: dict[str, Any] | None = None
    failure_reason: str | None = None
    expires_at: datetime | None = None
    polling_interval_seconds: int | None = None
