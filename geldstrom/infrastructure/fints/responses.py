"""FinTS-specific response handling and serialization."""

from __future__ import annotations

from geldstrom.domain.connection import NeedRetryResponse as _BaseNeedRetryResponse
from geldstrom.utils import SubclassesMixin, decompress_datablob

DATA_BLOB_MAGIC_RETRY = b"python-fints_RETRY_DATABLOB"


class NeedRetryResponse(SubclassesMixin, _BaseNeedRetryResponse):
    """
    FinTS-specific retry response with datablob serialization support.

    Subclasses (e.g., NeedTANResponse) implement `get_data` and `_from_data_v1`.
    """

    @classmethod
    def from_data(cls, blob: bytes):
        """Restore a NeedRetryResponse subclass from a compressed datablob."""
        version, data = decompress_datablob(DATA_BLOB_MAGIC_RETRY, blob)

        if version == 1:
            for clazz in cls._all_subclasses():
                if clazz.__name__ == data["_class_name"]:
                    return clazz._from_data_v1(data)

        raise Exception("Invalid data blob data or version")


__all__ = [
    "DATA_BLOB_MAGIC_RETRY",
    "NeedRetryResponse",
]
