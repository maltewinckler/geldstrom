"""Result DTO for the get-tan-methods command."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from gateway.domain.banking_gateway import OperationStatus, TanMethod


class TanMethodsResultEnvelope(BaseModel, frozen=True):
    """Application result for TAN-method discovery requests."""

    status: OperationStatus
    methods: list[TanMethod] = []
    operation_id: str | None = None
    expires_at: datetime | None = None
    failure_reason: str | None = None
