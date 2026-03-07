"""Key status value object."""

from enum import StrEnum


class KeyStatus(StrEnum):
    """Status of an API key."""

    active = "active"
    revoked = "revoked"
