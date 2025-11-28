"""Protocol-agnostic session abstractions for bank connections."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from fints.domain.model.bank import BankRoute


@runtime_checkable
class SessionToken(Protocol):
    """
    Protocol-agnostic interface for authenticated sessions.

    This protocol defines the minimal contract that any session implementation
    must satisfy, regardless of the underlying banking protocol (FinTS, PSD2,
    EBICS, etc.).

    Infrastructure adapters provide concrete implementations with protocol-specific
    details while conforming to this interface.
    """

    @property
    def user_id(self) -> str:
        """User identifier for this session."""
        ...

    @property
    def is_valid(self) -> bool:
        """Whether the session is still valid (not expired or revoked)."""
        ...

    def serialize(self) -> bytes:
        """
        Serialize session state for storage or transfer.

        Returns an opaque byte sequence that can be used to restore the session
        via the corresponding deserialize class method of the concrete implementation.
        """
        ...


class SessionHandle(BaseModel, frozen=True):
    """
    Lightweight, protocol-agnostic representation of an authenticated session.

    This is a simple domain value object for cases where only basic session
    information is needed. Concrete protocol implementations (FinTS, PSD2, etc.)
    should implement the SessionToken protocol with protocol-specific state.
    """

    route: BankRoute
    user_id: str
    token: bytes
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_valid(self) -> bool:
        """Sessions are valid unless explicitly invalidated."""
        return True

    def serialize(self) -> bytes:
        """Serialize to bytes via token field."""
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
    def from_dict(cls, data: Mapping[str, Any]) -> "SessionHandle":
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
