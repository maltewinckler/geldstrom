"""FinTS security mechanism protocols.

This module defines the protocols for encryption and authentication mechanisms.
The actual implementations are in fints.infrastructure.fints.auth.standalone_mechanisms.

For new code, use:
    from geldstrom.infrastructure.fints.auth import (
        StandaloneEncryptionMechanism,
        StandaloneAuthenticationMechanism,
    )
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from geldstrom.message import FinTSMessage


class EncryptionMechanism(Protocol):
    """Protocol for message encryption mechanisms."""

    def encrypt(self, message: "FinTSMessage") -> None:
        """Encrypt the message in place."""
        ...

    def decrypt(self, message: "FinTSMessage") -> None:
        """Decrypt the message in place."""
        ...


class AuthenticationMechanism(Protocol):
    """Protocol for message authentication/signing mechanisms."""

    def sign_prepare(self, message: "FinTSMessage") -> None:
        """Prepare the message for signing (add signature header)."""
        ...

    def sign_commit(self, message: "FinTSMessage") -> None:
        """Complete the signature (add signature trailer)."""
        ...

    def verify(self, message: "FinTSMessage") -> None:
        """Verify the message signature."""
        ...


# Re-export implementations for backward compatibility
# New code should import from geldstrom.infrastructure.fints.auth
def __getattr__(name: str):
    """Lazy import for deprecated implementations."""
    deprecated_names = {
        "PinTanDummyEncryptionMechanism",
        "PinTanAuthenticationMechanism",
        "PinTanOneStepAuthenticationMechanism",
        "PinTanTwoStepAuthenticationMechanism",
    }

    if name in deprecated_names:
        import warnings
        warnings.warn(
            f"{name} is deprecated. Use StandaloneEncryptionMechanism or "
            "StandaloneAuthenticationMechanism from geldstrom.infrastructure.fints.auth instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        from geldstrom.infrastructure.fints.auth import standalone_mechanisms
        return getattr(standalone_mechanisms, name, None)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "EncryptionMechanism",
    "AuthenticationMechanism",
]
