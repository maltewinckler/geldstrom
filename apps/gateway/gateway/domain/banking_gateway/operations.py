"""Operation state models for transient banking flows."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, field_validator, model_validator

from gateway.domain import DomainError


class BankProtocol(StrEnum):
    """Externally selectable banking protocols supported by the gateway."""

    FINTS = "fints"


class OperationStatus(StrEnum):
    """Application-visible state for a bank operation."""

    PENDING_CONFIRMATION = "pending_confirmation"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class OperationType(StrEnum):
    """Supported banking operation types."""

    ACCOUNTS = "accounts"
    BALANCES = "balances"
    TRANSACTIONS = "transactions"
    TAN_METHODS = "tan_methods"


class TanMethod(BaseModel, frozen=True):
    """Gateway-owned TAN method representation."""

    method_id: str
    display_name: str
    is_decoupled: bool

    @field_validator("method_id", "display_name")
    @classmethod
    def _must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise DomainError("TanMethod field must not be empty")
        return v


class PendingOperationSession(BaseModel):
    """Ephemeral runtime state for a decoupled bank operation."""

    operation_id: str
    consumer_id: UUID
    protocol: BankProtocol
    operation_type: OperationType
    session_state: bytes | None
    status: OperationStatus
    created_at: datetime
    expires_at: datetime
    last_polled_at: datetime | None = None
    result_payload: dict[str, Any] | None = None
    failure_reason: str | None = None

    @model_validator(mode="after")
    def _validate(self) -> PendingOperationSession:
        if not self.operation_id.strip():
            raise DomainError("PendingOperationSession.operation_id must not be empty")
        if (
            self.status is OperationStatus.PENDING_CONFIRMATION
            and not self.session_state
        ):
            raise DomainError(
                "PendingOperationSession.session_state must not be empty "
                "for pending sessions"
            )
        if self.expires_at <= self.created_at:
            raise DomainError(
                "PendingOperationSession.expires_at must be after created_at"
            )
        if self.status is OperationStatus.COMPLETED and self.result_payload is None:
            raise DomainError(
                "Completed PendingOperationSession instances must have a result_payload"
            )
        if self.status is OperationStatus.FAILED and not self.failure_reason:
            raise DomainError(
                "Failed PendingOperationSession instances must have a failure_reason"
            )
        if (
            self.status is OperationStatus.PENDING_CONFIRMATION
            and self.result_payload is not None
        ):
            raise DomainError(
                "Pending confirmation sessions must not have a result_payload"
            )
        return self


class AccountsResult(BaseModel):
    """Connector result for account listing flows."""

    status: OperationStatus
    accounts: list[dict[str, Any]] = []
    session_state: bytes = b""
    expires_at: datetime | None = None
    failure_reason: str | None = None

    @model_validator(mode="after")
    def _validate(self) -> AccountsResult:
        _validate_connector_result(
            status=self.status,
            session_state=self.session_state,
            expires_at=self.expires_at,
            failure_reason=self.failure_reason,
        )
        return self


class TransactionsResult(BaseModel):
    """Connector result for transaction-history flows."""

    status: OperationStatus
    transactions: list[dict[str, Any]] = []
    session_state: bytes = b""
    expires_at: datetime | None = None
    failure_reason: str | None = None

    @model_validator(mode="after")
    def _validate(self) -> TransactionsResult:
        _validate_connector_result(
            status=self.status,
            session_state=self.session_state,
            expires_at=self.expires_at,
            failure_reason=self.failure_reason,
        )
        return self


class BalancesResult(BaseModel):
    """Connector result for balance query flows."""

    status: OperationStatus
    balances: list[dict[str, Any]] = []
    session_state: bytes = b""
    expires_at: datetime | None = None
    failure_reason: str | None = None

    @model_validator(mode="after")
    def _validate(self) -> BalancesResult:
        _validate_connector_result(
            status=self.status,
            session_state=self.session_state,
            expires_at=self.expires_at,
            failure_reason=self.failure_reason,
        )
        return self


class TanMethodsResult(BaseModel):
    """Connector result for TAN-method discovery flows."""

    status: OperationStatus
    methods: list[TanMethod] = []
    session_state: bytes = b""
    expires_at: datetime | None = None
    failure_reason: str | None = None

    @model_validator(mode="after")
    def _validate(self) -> TanMethodsResult:
        _validate_connector_result(
            status=self.status,
            session_state=self.session_state,
            expires_at=self.expires_at,
            failure_reason=self.failure_reason,
        )
        return self


class ResumeResult(BaseModel):
    """Connector result when resuming a pending decoupled operation."""

    status: OperationStatus
    operation_type: OperationType | None = None
    session_state: bytes = b""
    result_payload: dict[str, Any] | None = None
    expires_at: datetime | None = None
    failure_reason: str | None = None

    @model_validator(mode="after")
    def _validate(self) -> ResumeResult:
        _validate_connector_result(
            status=self.status,
            session_state=self.session_state,
            expires_at=self.expires_at,
            failure_reason=self.failure_reason,
        )
        if self.status is OperationStatus.COMPLETED and self.result_payload is None:
            raise DomainError(
                "Completed ResumeResult instances must have a result_payload"
            )
        return self


def _validate_connector_result(
    *,
    status: OperationStatus,
    session_state: bytes,
    expires_at: datetime | None,
    failure_reason: str | None,
) -> None:
    if status is OperationStatus.PENDING_CONFIRMATION:
        if not session_state:
            raise DomainError("Pending confirmation results must include session_state")
        if expires_at is None:
            raise DomainError("Pending confirmation results must include expires_at")
    if status is OperationStatus.FAILED and not failure_reason:
        raise DomainError("Failed results must include a failure_reason")
