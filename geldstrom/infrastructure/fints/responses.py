"""FinTS-specific response handling and serialization."""
from __future__ import annotations

from enum import Enum

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


class ResponseStatus(Enum):
    """Error level reported by the FinTS dialog response."""

    UNKNOWN = 0
    SUCCESS = 1
    WARNING = 2
    ERROR = 3


RESPONSE_STATUS_MAPPING = {
    "0": ResponseStatus.SUCCESS,
    "3": ResponseStatus.WARNING,
    "9": ResponseStatus.ERROR,
}


class TransactionResponse:
    """Result of a FinTS operation."""

    status = ResponseStatus
    responses = list
    data = dict

    def __init__(self, response_message, segment_cls=None):
        self.status = ResponseStatus.UNKNOWN
        self.responses = []
        self.data = {}

        if segment_cls is None:
            raise ValueError("TransactionResponse requires a dialog segment class")

        for hirms in response_message.find_segments(segment_cls):
            for resp in hirms.responses:
                self.set_status_if_higher(
                    RESPONSE_STATUS_MAPPING.get(resp.code[0], ResponseStatus.UNKNOWN)
                )

    def set_status_if_higher(self, status: ResponseStatus) -> None:
        if status.value > self.status.value:
            self.status = status

    def __repr__(self):  # pragma: no cover - debugging helper
        return (
            "<{o.__class__.__name__}(status={o.status!r}, "
            "responses={o.responses!r}, data={o.data!r})>"
        ).format(o=self)


__all__ = [
    "NeedRetryResponse",
    "ResponseStatus",
    "TransactionResponse",
    "RESPONSE_STATUS_MAPPING",
    "DATA_BLOB_MAGIC_RETRY",
]
