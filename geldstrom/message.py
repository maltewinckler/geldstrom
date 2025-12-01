from enum import Enum
from typing import Any, ClassVar, Optional

from .infrastructure.fints.protocol import HIRMS2, SegmentSequence
from .infrastructure.fints.protocol.base import FinTSSegment as PydanticSegment


class MessageDirection(Enum):
    FROM_CUSTOMER = 1
    FROM_INSTITUTE = 2


class FinTSMessage(SegmentSequence):
    """Base class for FinTS messages.

    Extends SegmentSequence with message-level functionality:
    - Auto-numbering of segments
    - Dialog association
    - Response lookup
    """

    DIRECTION: ClassVar[Optional[MessageDirection]] = None

    # Non-model fields (excluded from Pydantic)
    model_config = {"arbitrary_types_allowed": True}

    # Instance attributes (not Pydantic fields)
    _dialog: Any = None
    _next_segment_number: int = 1

    def __init__(self, dialog=None, **kwargs):
        super().__init__(**kwargs)
        self._dialog = dialog
        self._next_segment_number = 1

    @property
    def dialog(self):
        return self._dialog

    @dialog.setter
    def dialog(self, value):
        self._dialog = value

    @property
    def next_segment_number(self):
        return self._next_segment_number

    @next_segment_number.setter
    def next_segment_number(self, value):
        self._next_segment_number = value

    def __iadd__(self, segment: PydanticSegment):
        """Append a segment to the message.

        Only Pydantic segments are supported for outgoing messages.
        """
        if not isinstance(segment, PydanticSegment):
            raise TypeError(
                "Can only append PydanticSegment instances, not {!r}".format(segment)
            )
        segment.header.number = self.next_segment_number
        self.next_segment_number += 1
        self.segments.append(segment)
        return self

    def response_segments(self, ref, *args, **kwargs):
        for segment in self.find_segments(*args, **kwargs):
            if segment.header.reference == ref.header.number:
                yield segment

    def responses(self, ref, code=None):
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
