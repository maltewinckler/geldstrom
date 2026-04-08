"""Result DTO for the get-operation-status query."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from gateway.domain.banking_gateway import OperationStatus


class OperationStatusEnvelope(BaseModel, frozen=True):
    """Application result for operation-status requests."""

    status: OperationStatus
    operation_id: str
    result_payload: dict[str, Any] | None = None
    failure_reason: str | None = None
    expires_at: datetime | None = None
