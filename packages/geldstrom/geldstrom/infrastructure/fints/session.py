"""FinTS-specific session state with protocol details."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from geldstrom.domain.model.bank import BankRoute


@dataclass(frozen=True)
class FinTSSessionState:
    """
    Snapshot of everything required to resume a read-only FinTS session.

    Implements the SessionToken protocol from the domain layer while
    providing FinTS 3.0-specific session details like system_id and
    bank parameter versions.
    """

    route: BankRoute
    user_id: str
    system_id: str
    client_blob: bytes
    bpd_version: int | None = None
    upd_version: int | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    version: str = "1"

    # --- SessionToken protocol implementation ---

    @property
    def is_valid(self) -> bool:
        """FinTS sessions remain valid until explicitly closed or system_id changes."""
        return bool(self.system_id)

    def serialize(self) -> bytes:
        """Serialize session state to JSON bytes for storage/transfer."""
        return json.dumps(self.to_dict()).encode("utf-8")

    @classmethod
    def deserialize(cls, data: bytes) -> FinTSSessionState:
        """Restore session state from serialized JSON bytes."""
        return cls.from_dict(json.loads(data.decode("utf-8")))

    # --- FinTS-specific methods ---

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "route": {
                "country_code": self.route.country_code,
                "bank_code": self.route.bank_code,
            },
            "user_id": self.user_id,
            "system_id": self.system_id,
            "bpd_version": self.bpd_version,
            "upd_version": self.upd_version,
            "client_blob": self.client_blob.hex(),
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> FinTSSessionState:
        route = BankRoute(
            country_code=data["route"]["country_code"],
            bank_code=data["route"]["bank_code"],
        )
        created_at = datetime.fromisoformat(data["created_at"])
        return cls(
            route=route,
            user_id=data["user_id"],
            system_id=data["system_id"],
            bpd_version=(
                int(data["bpd_version"])
                if data.get("bpd_version") is not None
                else None
            ),
            upd_version=(
                int(data["upd_version"])
                if data.get("upd_version") is not None
                else None
            ),
            client_blob=bytes.fromhex(data["client_blob"]),
            created_at=created_at,
            version=str(data.get("version", "1")),
        )

    def mask(self) -> dict[str, Any]:
        """Return a representation safe for logging (client_blob redacted)."""
        masked = self.to_dict()
        masked["client_blob"] = f"<{len(self.client_blob)} bytes>"
        return masked


# Backward compatibility alias
SessionState = FinTSSessionState
