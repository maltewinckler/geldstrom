"""FinTS-specific TAN method descriptors returned by HITANS segments."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TANMethod(BaseModel, frozen=True):
    """Describes a single TAN authentication method advertised by the bank."""

    code: str = Field(description="Security function code (e.g., '920', '946')")
    name: str = Field(description="Human-readable name (e.g., 'SecureGo+')")

    technical_id: str | None = Field(default=None)
    zka_id: str | None = Field(default=None)
    zka_version: str | None = Field(default=None)
    max_tan_length: int | None = Field(default=None, ge=0)
    is_decoupled: bool = Field(default=False)
    decoupled_max_polls: int | None = Field(default=None)
    decoupled_first_poll_delay: int | None = Field(default=None)
    decoupled_poll_interval: int | None = Field(default=None)
    supports_cancel: bool = Field(default=False)
    supports_multiple_tan: bool = Field(default=False)

    def __str__(self) -> str:
        return f"{self.code}: {self.name}"


__all__ = ["TANMethod"]
