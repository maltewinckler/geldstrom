"""Key hash value object."""

from pydantic import BaseModel


class KeyHash(BaseModel, frozen=True):
    """Argon2id hash string.

    Constructed only via KeyHasher port.
    """

    value: str
