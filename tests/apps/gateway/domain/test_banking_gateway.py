"""Tests for the banking gateway domain."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from gateway.domain import DomainError
from gateway.domain.banking_gateway import (
    BankProtocol,
    OperationStatus,
    PendingOperationSession,
    PresentedBankCredentials,
    RequestedIban,
)


def test_presented_bank_credentials_rejects_blank_user_id() -> None:
    with pytest.raises(Exception, match="blank"):
        PresentedBankCredentials(
            user_id="   ",
            password="123456",
        )


def test_requested_iban_normalizes_and_validates_checksum() -> None:
    iban = RequestedIban("de89 3704 0044 0532 0130 00")

    assert iban.value == "DE89370400440532013000"


def test_requested_iban_rejects_invalid_values() -> None:
    with pytest.raises(DomainError, match="checksum"):
        RequestedIban("DE89370400440532013001")


def test_pending_operation_session_constructs_with_pending_state() -> None:
    created_at = datetime.now(tz=UTC)
    session = PendingOperationSession(
        operation_id="operation-123",
        consumer_id=UUID("12345678-1234-5678-1234-567812345678"),
        protocol=BankProtocol.FINTS,
        operation_type="transactions",
        session_state=b"opaque-session-state",
        status=OperationStatus.PENDING_CONFIRMATION,
        created_at=created_at,
        expires_at=created_at + timedelta(minutes=5),
    )

    assert session.operation_id == "operation-123"
    assert session.status is OperationStatus.PENDING_CONFIRMATION
    assert session.last_polled_at is None
