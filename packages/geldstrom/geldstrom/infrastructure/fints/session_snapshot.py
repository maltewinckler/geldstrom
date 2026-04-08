"""Serializable snapshot of a decoupled TAN session for external storage.

A ``DecoupledSessionSnapshot`` captures everything needed to resume polling
a bank for TAN approval **without** storing any user credentials.  The
gateway serialises this into Redis and reconstructs the FinTS dialog from
fresh credentials supplied by the client on each poll request.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


def _json_default(obj: object) -> str:
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class DecoupledSessionSnapshot(BaseModel, frozen=True):
    """Credential-free snapshot of a pending decoupled TAN session."""

    # Serialised DialogSnapshot dict (dialog_id, message_number, …)
    dialog_snapshot: dict[str, Any]

    # HKTAN task reference needed for poll_decoupled_once()
    task_reference: str

    # Serialised ParameterStore + system_id (FinTSSessionState.serialize())
    fints_session_state: bytes

    # Bank endpoint URL needed to re-open the HTTPS connection
    server_url: str

    # Which operation was originally requested (accounts, transactions, …)
    operation_type: str

    # Extra metadata needed to complete the operation after TAN approval
    # (e.g. account_id, start_date, end_date for transactions)
    operation_meta: dict[str, Any] = {}

    def serialize(self) -> bytes:
        """Encode to JSON bytes for storage in Redis / session store."""
        payload = {
            "dialog_snapshot": self.dialog_snapshot,
            "task_reference": self.task_reference,
            "fints_session_state": self.fints_session_state.hex(),
            "server_url": self.server_url,
            "operation_type": self.operation_type,
            "operation_meta": self.operation_meta,
        }
        return json.dumps(
            payload, sort_keys=True, separators=(",", ":"), default=_json_default
        ).encode()

    @classmethod
    def deserialize(cls, data: bytes) -> DecoupledSessionSnapshot:
        """Reconstruct from JSON bytes produced by ``serialize()``."""
        parsed = json.loads(data)
        return cls(
            dialog_snapshot=parsed["dialog_snapshot"],
            task_reference=parsed["task_reference"],
            fints_session_state=bytes.fromhex(parsed["fints_session_state"]),
            server_url=parsed["server_url"],
            operation_type=parsed["operation_type"],
            operation_meta=parsed.get("operation_meta", {}),
        )
