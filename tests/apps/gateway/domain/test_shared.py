"""Tests for shared gateway domain primitives."""

from uuid import UUID

from gateway.domain.banking_gateway import BankProtocol


def test_consumer_id_is_a_plain_uuid() -> None:
    consumer_id = UUID("12345678-1234-5678-1234-567812345678")
    assert str(consumer_id) == "12345678-1234-5678-1234-567812345678"


def test_bank_protocol_contains_fints() -> None:
    assert BankProtocol.FINTS.value == "fints"
