"""Result DTO for the fetch-transactions command."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from gateway.domain.banking_gateway import OperationStatus


class TransactionsResultEnvelope(BaseModel, frozen=True):
    """Application result for transaction-history requests."""

    status: OperationStatus
    transactions: list[dict[str, Any]] = []
    operation_id: str | None = None
    expires_at: datetime | None = None
    failure_reason: str | None = None
