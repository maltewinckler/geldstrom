"""FinTS-specific TAN method descriptors returned by HITANS segments."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TANMethod(BaseModel, frozen=True):
    """Describes a single TAN authentication method advertised by the bank."""

    code: str = Field(description="Security function code (e.g., '920', '946')")
    name: str = Field(description="Human-readable name (e.g., 'SecureGo+')")

    # Technical details
    technical_id: str | None = Field(
        default=None,
        description="Technical identifier for the method",
    )
    zka_id: str | None = Field(
        default=None,
        description="ZKA (Zentraler Kreditausschuss) identifier",
    )
    zka_version: str | None = Field(
        default=None,
        description="Version of the ZKA standard",
    )

    # Input constraints
    max_tan_length: int | None = Field(
        default=None,
        ge=0,
        description="Maximum length of TAN input",
    )

    # Decoupled-specific properties
    is_decoupled: bool = Field(
        default=False,
        description="True if this is a decoupled (app-based) method",
    )
    decoupled_max_polls: int | None = Field(
        default=None,
        description="Maximum status polls for decoupled TAN",
    )
    decoupled_first_poll_delay: int | None = Field(
        default=None,
        description="Seconds to wait before first poll",
    )
    decoupled_poll_interval: int | None = Field(
        default=None,
        description="Seconds between subsequent polls",
    )

    # Feature flags
    supports_cancel: bool = Field(
        default=False,
        description="Whether pending TANs can be cancelled",
    )
    supports_multiple_tan: bool = Field(
        default=False,
        description="Whether multiple TANs can be active",
    )

    def __str__(self) -> str:
        return f"{self.code}: {self.name}"


__all__ = ["TANMethod"]
