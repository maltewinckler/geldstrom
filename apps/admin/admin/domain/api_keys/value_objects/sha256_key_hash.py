"""SHA-256 key hash value object."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from admin.domain.api_keys.value_objects.raw_key import RawKey


class SHA256KeyHash(BaseModel, frozen=True):
    """SHA-256 hex digest of a RawKey.

    Used for gRPC lookup.
    """

    value: str

    @classmethod
    def from_raw_key(cls, raw_key: RawKey) -> SHA256KeyHash:
        """Compute SHA-256 hash from a raw key."""
        digest = hashlib.sha256(raw_key.value.get_secret_value().encode()).hexdigest()
        return cls(value=digest)
