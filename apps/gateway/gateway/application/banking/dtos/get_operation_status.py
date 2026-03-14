"""Result DTO for the get-operation-status query."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from gateway.domain.banking_gateway import OperationStatus


@dataclass(frozen=True)
class OperationStatusEnvelope:
    """Application result for operation-status requests."""

    status: OperationStatus
    operation_id: str
    result_payload: dict[str, Any] | None = None
    failure_reason: str | None = None
    expires_at: datetime | None = None
