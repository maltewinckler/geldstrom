"""Result DTO for the list-accounts command."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from gateway.domain.banking_gateway import OperationStatus


class ListAccountsResultEnvelope(BaseModel, frozen=True):
    """Application result for account-listing requests."""

    status: OperationStatus
    accounts: list[dict[str, Any]] = []
    operation_id: str | None = None
    expires_at: datetime | None = None
    failure_reason: str | None = None
