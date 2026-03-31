"""Domain objects describing TAN authentication methods."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class TANMethodType(StrEnum):
    """Types of TAN authentication methods."""

    DECOUPLED = "decoupled"  # App-based approval (SecureGo+, etc.)
    PUSH = "push"  # Push notification
    SMS = "sms"  # SMS TAN
    CHIPTAN = "chiptan"  # Chip-based TAN generator
    PHOTO_TAN = "photo_tan"  # Photo/QR-based TAN
    MANUAL = "manual"  # Manual TAN entry
    UNKNOWN = "unknown"


class TANMethod(BaseModel, frozen=True):
    """
    Describes a TAN (Transaction Authentication Number) method.

    TAN methods are used for two-factor authentication (2FA) in German
    online banking. Each bank supports different methods, and users may
    have multiple methods configured.

    Example:
        >>> method = TANMethod(code="920", name="SecureGo+", is_decoupled=True)
        >>> print(method)
        920: SecureGo+
    """

    code: str = Field(description="Security function code (e.g., '920', '946')")
    name: str = Field(description="Human-readable name (e.g., 'SecureGo+')")
    method_type: TANMethodType = Field(
        default=TANMethodType.UNKNOWN,
        description="Classification of the TAN method",
    )

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


__all__ = [
    "TANMethod",
    "TANMethodType",
]
