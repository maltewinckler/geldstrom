"""FinTS message types for dialog communication."""

from enum import Enum
from typing import ClassVar

from geldstrom.infrastructure.fints.protocol import HIRMS2, SegmentSequence
from geldstrom.infrastructure.fints.protocol.base import FinTSSegment


class MessageDirection(Enum):
    FROM_CUSTOMER = 1
    FROM_INSTITUTE = 2


class FinTSMessage(SegmentSequence):
    """Base class for FinTS messages."""

    DIRECTION: ClassVar[MessageDirection | None] = None

    # Non-model fields (excluded from Pydantic)
    model_config = {"arbitrary_types_allowed": True}

    _next_segment_number: int = 1

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._next_segment_number = 1

    @property
    def next_segment_number(self):
        return self._next_segment_number

    @next_segment_number.setter
    def next_segment_number(self, value):
        self._next_segment_number = value

    def __iadd__(self, segment: FinTSSegment):
        """Append a segment to the message."""
        if not isinstance(segment, FinTSSegment):
            raise TypeError(f"Can only append FinTSSegment instances, not {segment!r}")
        segment.header.number = self.next_segment_number
        self.next_segment_number += 1
        self.segments.append(segment)
        return self

    def response_segments(self, ref, *args, **kwargs):
        """Yield response segments for a given reference segment."""
        for segment in self.find_segments(*args, **kwargs):
            if segment.header.reference == ref.header.number:
                yield segment

    def responses(self, ref, code=None):
        """Yield response entries for a given reference segment."""
        for segment in self.response_segments(ref, HIRMS2):
            for response in segment.responses:
                if code is None or response.code == code:
                    yield response


class FinTSCustomerMessage(FinTSMessage):
    """Message sent from customer to bank."""

    DIRECTION: ClassVar[MessageDirection] = MessageDirection.FROM_CUSTOMER


class FinTSInstituteMessage(FinTSMessage):
    """Message received from bank."""

    DIRECTION: ClassVar[MessageDirection] = MessageDirection.FROM_INSTITUTE


__all__ = [
    "FinTSCustomerMessage",
    "FinTSInstituteMessage",
    "FinTSMessage",
    "MessageDirection",
]
