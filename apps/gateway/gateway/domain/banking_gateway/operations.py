"""Operation state models for transient banking flows."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from gateway.domain import DomainError

_ALLOWED_OPERATION_TYPES = ("accounts", "balances", "transactions", "tan_methods")


class BankProtocol(StrEnum):
    """Externally selectable banking protocols supported by the gateway."""

    FINTS = "fints"


class OperationStatus(StrEnum):
    """Application-visible state for a bank operation."""

    PENDING_CONFIRMATION = "pending_confirmation"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass(frozen=True)
class TanMethod:
    """Gateway-owned TAN method representation."""

    method_id: str
    display_name: str
    is_decoupled: bool

    def __post_init__(self) -> None:
        if not self.method_id.strip():
            raise DomainError("TanMethod.method_id must not be empty")
        if not self.display_name.strip():
            raise DomainError("TanMethod.display_name must not be empty")


@dataclass
class PendingOperationSession:
    """Ephemeral runtime state for a decoupled bank operation."""

    operation_id: str
    consumer_id: UUID
    protocol: BankProtocol
    operation_type: str
    session_state: bytes
    status: OperationStatus
    created_at: datetime
    expires_at: datetime
    last_polled_at: datetime | None = None
    result_payload: dict[str, Any] | None = None
    failure_reason: str | None = None

    def __post_init__(self) -> None:
        if not self.operation_id.strip():
            raise DomainError("PendingOperationSession.operation_id must not be empty")
        if self.operation_type not in _ALLOWED_OPERATION_TYPES:
            raise DomainError(
                "PendingOperationSession.operation_type must be accounts, transactions, or tan_methods"
            )
        if not self.session_state:
            raise DomainError("PendingOperationSession.session_state must not be empty")
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


@dataclass
class AccountsResult:
    """Connector result for account listing flows."""

    status: OperationStatus
    accounts: list[dict[str, Any]] = field(default_factory=list)
    session_state: bytes = b""
    expires_at: datetime | None = None
    failure_reason: str | None = None

    def __post_init__(self) -> None:
        _validate_connector_result(
            status=self.status,
            session_state=self.session_state,
            expires_at=self.expires_at,
            failure_reason=self.failure_reason,
        )


@dataclass
class TransactionsResult:
    """Connector result for transaction-history flows."""

    status: OperationStatus
    transactions: list[dict[str, Any]] = field(default_factory=list)
    session_state: bytes = b""
    expires_at: datetime | None = None
    failure_reason: str | None = None

    def __post_init__(self) -> None:
        _validate_connector_result(
            status=self.status,
            session_state=self.session_state,
            expires_at=self.expires_at,
            failure_reason=self.failure_reason,
        )


@dataclass
class BalancesResult:
    """Connector result for balance query flows."""

    status: OperationStatus
    balances: list[dict[str, Any]] = field(default_factory=list)
    session_state: bytes = b""
    expires_at: datetime | None = None
    failure_reason: str | None = None

    def __post_init__(self) -> None:
        _validate_connector_result(
            status=self.status,
            session_state=self.session_state,
            expires_at=self.expires_at,
            failure_reason=self.failure_reason,
        )


@dataclass
class TanMethodsResult:
    """Connector result for TAN-method discovery flows."""

    status: OperationStatus
    methods: list[TanMethod] = field(default_factory=list)
    session_state: bytes = b""
    expires_at: datetime | None = None
    failure_reason: str | None = None

    def __post_init__(self) -> None:
        _validate_connector_result(
            status=self.status,
            session_state=self.session_state,
            expires_at=self.expires_at,
            failure_reason=self.failure_reason,
        )


@dataclass
class ResumeResult:
    """Connector result when resuming a pending decoupled operation."""

    status: OperationStatus
    session_state: bytes = b""
    result_payload: dict[str, Any] | None = None
    expires_at: datetime | None = None
    failure_reason: str | None = None

    def __post_init__(self) -> None:
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
