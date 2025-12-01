"""Response processing for FinTS dialog messages."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Sequence

from fints.message import FinTSInstituteMessage
from fints.infrastructure.fints.protocol import HIBPA3, HIUPA4, HIRMG2, HIRMS2, HNHBK3
from fints.types import SegmentSequence

logger = logging.getLogger(__name__)


class ResponseLevel(Enum):
    """Severity level for dialog responses."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class DialogResponse:
    """A single response code and message from the bank."""

    code: str
    text: str
    parameters: Sequence[str] = field(default_factory=tuple)

    @property
    def level(self) -> ResponseLevel:
        """Determine the severity level from the response code."""
        if self.code.startswith("0") or self.code.startswith("1"):
            return ResponseLevel.INFO
        elif self.code.startswith("3"):
            return ResponseLevel.WARNING
        else:
            return ResponseLevel.ERROR

    @property
    def is_success(self) -> bool:
        """Return True if this is a success response."""
        return self.code.startswith("0")

    @property
    def is_error(self) -> bool:
        """Return True if this is an error response."""
        return self.code.startswith("9")


@dataclass
class ProcessedResponse:
    """Result of processing a FinTS institute response."""

    dialog_id: str
    message_number: int
    global_responses: Sequence[DialogResponse]
    segment_responses: Sequence[DialogResponse]
    bpd_version: int | None = None
    upd_version: int | None = None
    bpd_segments: SegmentSequence | None = None
    upd_segments: SegmentSequence | None = None
    bpa: object | None = None  # HIBPA segment
    upa: object | None = None  # HIUPA segment
    raw_response: "FinTSInstituteMessage | None" = None  # Full response for segment access

    @property
    def has_errors(self) -> bool:
        """Return True if any response is an error."""
        return any(r.is_error for r in self.all_responses)

    @property
    def all_responses(self) -> Sequence[DialogResponse]:
        """Return all responses (global and segment-level)."""
        return list(self.global_responses) + list(self.segment_responses)

    def get_response_by_code(self, code: str) -> DialogResponse | None:
        """Find a response by its code."""
        for resp in self.all_responses:
            if resp.code == code:
                return resp
        return None

    def find_segment_first(self, segment_type) -> object | None:
        """
        Find the first segment of a given type in the raw response.

        Args:
            segment_type: Segment class to search for

        Returns:
            First matching segment or None
        """
        if self.raw_response is None:
            return None
        return self.raw_response.find_segment_first(segment_type)


ResponseCallback = Callable[[DialogResponse, object | None], None]


class ResponseProcessor:
    """
    Processes FinTS institute responses and extracts relevant data.

    This class handles:
    - Extracting dialog ID from response headers
    - Parsing global (HIRMG) and segment-level (HIRMS) responses
    - Extracting bank parameter data (BPD) updates
    - Extracting user parameter data (UPD) updates
    - Invoking callbacks for response handling
    """

    def __init__(self) -> None:
        """Initialize the response processor."""
        self._callbacks: list[ResponseCallback] = []

    def add_callback(self, callback: ResponseCallback) -> None:
        """Add a callback to be invoked for each response."""
        self._callbacks.append(callback)

    def remove_callback(self, callback: ResponseCallback) -> None:
        """Remove a previously added callback."""
        self._callbacks.remove(callback)

    def process(self, response: FinTSInstituteMessage) -> ProcessedResponse:
        """
        Process an institute response message.

        Args:
            response: The institute response to process

        Returns:
            ProcessedResponse with extracted data
        """
        # Extract dialog ID and message number
        header = response.find_segment_first(HNHBK3)
        dialog_id = header.dialog_id if header else "0"
        message_number = header.message_number if header else 0

        # Extract global responses (HIRMG)
        global_responses = self._extract_global_responses(response)

        # Extract segment responses (HIRMS)
        segment_responses = self._extract_segment_responses(response)

        # Extract BPD updates
        bpa, bpd_version, bpd_segments = self._extract_bpd(response)

        # Extract UPD updates
        upa, upd_version, upd_segments = self._extract_upd(response)

        # Invoke callbacks
        all_responses = list(global_responses) + list(segment_responses)
        for resp in all_responses:
            self._invoke_callbacks(resp, None)

        return ProcessedResponse(
            dialog_id=dialog_id,
            message_number=message_number,
            global_responses=global_responses,
            segment_responses=segment_responses,
            bpd_version=bpd_version,
            upd_version=upd_version,
            bpd_segments=bpd_segments,
            upd_segments=upd_segments,
            bpa=bpa,
            upa=upa,
            raw_response=response,
        )

    def _extract_global_responses(
        self, response: FinTSInstituteMessage
    ) -> Sequence[DialogResponse]:
        """Extract global (message-level) responses from HIRMG segments."""
        responses = []
        for seg in response.find_segments(HIRMG2):
            for resp in seg.responses:
                responses.append(
                    DialogResponse(
                        code=resp.code,
                        text=resp.text,
                        parameters=tuple(resp.parameters) if resp.parameters else (),
                    )
                )
        return tuple(responses)

    def _extract_segment_responses(
        self, response: FinTSInstituteMessage
    ) -> Sequence[DialogResponse]:
        """Extract segment-level responses from HIRMS segments."""
        responses = []
        for seg in response.find_segments(HIRMS2):
            for resp in seg.responses:
                responses.append(
                    DialogResponse(
                        code=resp.code,
                        text=resp.text,
                        parameters=tuple(resp.parameters) if resp.parameters else (),
                    )
                )
        return tuple(responses)

    def _extract_bpd(
        self, response: FinTSInstituteMessage
    ) -> tuple[object | None, int | None, SegmentSequence | None]:
        """Extract bank parameter data from response."""
        bpa = response.find_segment_first(HIBPA3)
        if not bpa:
            return None, None, None

        # Find all BPD segments (type pattern: HI???S)
        bpd_segments = SegmentSequence(
            response.find_segments(
                callback=lambda m: (
                    len(m.header.type) == 6
                    and m.header.type[1] == "I"
                    and m.header.type[5] == "S"
                )
            )
        )

        return bpa, bpa.bpd_version, bpd_segments

    def _extract_upd(
        self, response: FinTSInstituteMessage
    ) -> tuple[object | None, int | None, SegmentSequence | None]:
        """Extract user parameter data from response."""
        upa = response.find_segment_first(HIUPA4)
        if not upa:
            return None, None, None

        segments_iter = list(response.find_segments("HIUPD"))
        logger.warning("Response contains %d HIUPD segments", len(segments_iter))
        upd_segments = SegmentSequence(segments_iter)
        return upa, upa.upd_version, upd_segments

    def _invoke_callbacks(
        self, response: DialogResponse, segment: object | None
    ) -> None:
        """Invoke registered callbacks for a response."""
        for callback in self._callbacks:
            try:
                callback(response, segment)
            except Exception:
                logger.exception("Error in response callback")


def log_response(response: DialogResponse, segment: object | None = None) -> None:
    """Standard callback for logging responses."""
    if response.level == ResponseLevel.INFO:
        log_target = logger.info
    elif response.level == ResponseLevel.WARNING:
        log_target = logger.warning
    else:
        log_target = logger.error

    params_str = f" ({response.parameters!r})" if response.parameters else ""
    log_target(
        "Dialog response: %s - %s%s",
        response.code,
        response.text,
        params_str,
        extra={
            "fints_response_code": response.code,
            "fints_response_text": response.text,
            "fints_response_parameters": response.parameters,
        },
    )

