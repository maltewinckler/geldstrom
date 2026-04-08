"""Result DTO for the get-balances command."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from gateway.domain.banking_gateway import OperationStatus


class BalancesResultEnvelope(BaseModel, frozen=True):
    """Application result for balance-query requests."""

    status: OperationStatus
    balances: list[dict[str, Any]] = []
    operation_id: str | None = None
    expires_at: datetime | None = None
    failure_reason: str | None = None
