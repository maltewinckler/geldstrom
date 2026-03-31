"""Serialization helpers for opaque Geldstrom connector session state."""

from __future__ import annotations

import json
from datetime import date

from gateway.domain.banking_gateway.operations import OperationType
from geldstrom.infrastructure.fints.session import FinTSSessionState

from .models import SerializedPendingOperation


def serialize_pending_operation(operation: SerializedPendingOperation) -> bytes:
    payload = {
        "operation_type": operation.operation_type.value,
        "bank_code": operation.bank_code,
        "endpoint": operation.endpoint,
        "user_id": operation.user_id,
        "password": operation.password,
        "iban": operation.iban,
        "start_date": operation.start_date.isoformat()
        if operation.start_date
        else None,
        "end_date": operation.end_date.isoformat() if operation.end_date else None,
        "fints_session_state": operation.fints_session_state.hex(),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def deserialize_pending_operation(payload: bytes) -> SerializedPendingOperation:
    data = json.loads(payload.decode("utf-8"))
    return SerializedPendingOperation(
        operation_type=OperationType(data["operation_type"]),
        bank_code=data["bank_code"],
        endpoint=data["endpoint"],
        user_id=data["user_id"],
        password=data["password"],
        iban=data.get("iban"),
        start_date=date.fromisoformat(data["start_date"])
        if data.get("start_date")
        else None,
        end_date=date.fromisoformat(data["end_date"]) if data.get("end_date") else None,
        fints_session_state=bytes.fromhex(data["fints_session_state"]),
    )


def serialize_fints_session_state(session_state: FinTSSessionState) -> bytes:
    return session_state.serialize()


def deserialize_fints_session_state(payload: bytes) -> FinTSSessionState:
    return FinTSSessionState.deserialize(payload)
