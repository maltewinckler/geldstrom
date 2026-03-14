"""Tests for the banking gateway domain."""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import SecretStr

from gateway.domain.banking_gateway import (
    BankRequestSanitizationPolicy,
    OperationStatus,
    PendingOperationSession,
    PresentedBankCredentials,
    PresentedBankPassword,
    PresentedBankUserId,
    RequestedIban,
)
from gateway.domain.consumer_access import ConsumerId
from gateway.domain.shared import BankProtocol, DomainError


def test_bank_request_sanitization_policy_rejects_empty_secret_fields() -> None:
    credentials = PresentedBankCredentials(
        user_id=PresentedBankUserId(SecretStr("   ")),
        password=PresentedBankPassword(SecretStr("123456")),
    )

    with pytest.raises(DomainError, match="user id"):
        BankRequestSanitizationPolicy.sanitize(credentials)


def test_requested_iban_normalizes_and_validates_checksum() -> None:
    iban = RequestedIban("de89 3704 0044 0532 0130 00")

    assert iban.value == "DE89370400440532013000"


def test_requested_iban_rejects_invalid_values() -> None:
    with pytest.raises(DomainError, match="checksum"):
        RequestedIban("DE89370400440532013001")


def test_pending_operation_session_constructs_with_pending_state() -> None:
    created_at = datetime.now(tz=timezone.utc)
    session = PendingOperationSession(
        operation_id="operation-123",
        consumer_id=ConsumerId.from_string("12345678-1234-5678-1234-567812345678"),
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
