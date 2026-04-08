"""Tests for DecoupledSessionSnapshot serialization."""

from __future__ import annotations

import json

import pytest

from geldstrom.infrastructure.fints.session_snapshot import DecoupledSessionSnapshot


class TestDecoupledSessionSnapshot:
    """Round-trip and edge-case tests for DecoupledSessionSnapshot."""

    def _make_snapshot(self, **overrides) -> DecoupledSessionSnapshot:
        defaults = {
            "dialog_snapshot": {
                "dialog_id": "dlg-42",
                "message_number": 7,
                "country_identifier": "280",
                "bank_code": "12345678",
                "user_id": "testuser",
                "customer_id": "testuser",
                "system_id": "sys-abc",
                "product_name": "TestProd",
                "product_version": "1.0",
                "security_function": "946",
            },
            "task_reference": "task-ref-123",
            "fints_session_state": b"\xde\xad\xbe\xef",
            "server_url": "https://bank.example.com/fints",
            "operation_type": "transactions",
            "operation_meta": {
                "account_id": "DE123",
                "start_date": "2026-01-01",
                "end_date": "2026-03-31",
            },
        }
        defaults.update(overrides)
        return DecoupledSessionSnapshot(**defaults)

    def test_serialize_deserialize_round_trip(self):
        snapshot = self._make_snapshot()
        restored = DecoupledSessionSnapshot.deserialize(snapshot.serialize())

        assert restored.dialog_snapshot == snapshot.dialog_snapshot
        assert restored.task_reference == snapshot.task_reference
        assert restored.fints_session_state == snapshot.fints_session_state
        assert restored.server_url == snapshot.server_url
        assert restored.operation_type == snapshot.operation_type
        assert restored.operation_meta == snapshot.operation_meta

    def test_serialize_produces_valid_json(self):
        snapshot = self._make_snapshot()
        data = json.loads(snapshot.serialize())

        assert data["task_reference"] == "task-ref-123"
        assert data["server_url"] == "https://bank.example.com/fints"
        assert data["fints_session_state"] == "deadbeef"

    def test_no_credentials_in_serialized_output(self):
        """The serialized form must never contain user credentials."""
        snapshot = self._make_snapshot()
        raw = snapshot.serialize().decode()

        assert "password" not in raw.lower()
        assert "pin" not in raw.lower()
        assert "secret" not in raw.lower()

    def test_empty_operation_meta_defaults(self):
        snapshot = DecoupledSessionSnapshot(
            dialog_snapshot={"dialog_id": "d"},
            task_reference="t",
            fints_session_state=b"",
            server_url="https://x",
            operation_type="accounts",
        )
        assert snapshot.operation_meta == {}

        restored = DecoupledSessionSnapshot.deserialize(snapshot.serialize())
        assert restored.operation_meta == {}

    def test_frozen(self):
        snapshot = self._make_snapshot()
        with pytest.raises(Exception):
            snapshot.task_reference = "new"  # type: ignore[misc]
