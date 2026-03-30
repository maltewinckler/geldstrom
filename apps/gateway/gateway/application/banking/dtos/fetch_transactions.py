"""Result DTO for the fetch-transactions command."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from gateway.domain.banking_gateway import OperationStatus


@dataclass(frozen=True)
class TransactionsResultEnvelope:
    """Application result for transaction-history requests."""

    status: OperationStatus
    transactions: list[dict[str, Any]] = field(default_factory=list)
    operation_id: str | None = None
    expires_at: datetime | None = None
    failure_reason: str | None = None
