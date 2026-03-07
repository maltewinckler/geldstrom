"""Raw key value object."""

import secrets

from pydantic import BaseModel, SecretStr


class RawKey(BaseModel, frozen=True):
    """SecretStr wrapper for a 32-byte hex string (256-bit entropy).

    Exists only in process memory. Never persisted.
    """

    value: SecretStr

    @classmethod
    def generate(cls) -> "RawKey":
        """Generate a new cryptographically random raw key."""
        return cls(value=SecretStr(secrets.token_hex(32)))
