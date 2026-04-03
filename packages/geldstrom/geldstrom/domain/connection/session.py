"""Protocol-agnostic session abstractions for bank connections."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from geldstrom.domain.model.bank import BankRoute


@runtime_checkable
class SessionToken(Protocol):
    """Protocol-agnostic interface for authenticated bank sessions."""

    @property
    def user_id(self) -> str: ...

    @property
    def is_valid(self) -> bool: ...

    def serialize(self) -> bytes: ...


class SessionHandle(BaseModel, frozen=True):
    """Lightweight value object for basic session state."""

    route: BankRoute
    user_id: str
    token: bytes
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_valid(self) -> bool:
        return True

    def serialize(self) -> bytes:
        return self.token

    def to_dict(self) -> dict[str, Any]:
        return {
            "route": {
                "country_code": self.route.country_code,
                "bank_code": self.route.bank_code,
            },
            "user_id": self.user_id,
            "token": self.token.hex(),
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> SessionHandle:
        route = BankRoute(
            country_code=data["route"]["country_code"],
            bank_code=data["route"]["bank_code"],
        )
        return cls(
            route=route,
            user_id=data["user_id"],
            token=bytes.fromhex(data["token"]),
            created_at=datetime.fromisoformat(data["created_at"]),
        )
