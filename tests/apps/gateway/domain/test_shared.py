"""Tests for shared gateway domain primitives."""

from uuid import UUID

from gateway.domain.shared import BankProtocol, EntityId


def test_entity_id_wraps_uuid_value() -> None:
    entity_id = EntityId.from_string("12345678-1234-5678-1234-567812345678")

    assert entity_id.value == UUID("12345678-1234-5678-1234-567812345678")
    assert str(entity_id) == "12345678-1234-5678-1234-567812345678"


def test_bank_protocol_contains_fints() -> None:
    assert BankProtocol.FINTS.value == "fints"
