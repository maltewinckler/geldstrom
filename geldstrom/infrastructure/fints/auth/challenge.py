"""FinTS-specific TAN challenge handling."""

from __future__ import annotations

from base64 import b64decode
from dataclasses import dataclass
from typing import TYPE_CHECKING

import bleach

from geldstrom.domain.connection import Challenge, ChallengeData, ChallengeType
from geldstrom.infrastructure.fints import DATA_BLOB_MAGIC_RETRY, NeedRetryResponse
from geldstrom.infrastructure.fints.protocol.base import SegmentSequence
from geldstrom.utils import compress_datablob

if TYPE_CHECKING:
    pass


@dataclass
class ParsedChallenge:
    """Parsed challenge data from a TAN request segment."""

    raw_text: str
    display_text: str
    html_text: str | None
    hhduc_data: str | None  # Flicker code data
    matrix_data: tuple[str, bytes] | None  # (mime_type, image_data)


def parse_tan_challenge(
    tan_request,
    structured: bool = False,
) -> ParsedChallenge:
    """
    Parse challenge data from a TAN request segment.

    This extracts and decodes the various challenge formats used by
    different banks (text, HHD_UC flicker codes, matrix/QR codes).

    Args:
        tan_request: The HITAN segment containing the challenge
        structured: Whether the challenge text uses HTML formatting

    Returns:
        ParsedChallenge with extracted data
    """
    raw_text = tan_request.challenge or ""
    display_text = raw_text
    html_text = None
    hhduc_data = None
    matrix_data = None

    # Check for HHD_UC challenge data in the segment
    if hasattr(tan_request, "challenge_hhduc") and tan_request.challenge_hhduc:
        hhduc_bytes = tan_request.challenge_hhduc
        if len(hhduc_bytes) < 256:
            # Simple HHD_UC code
            hhduc_data = hhduc_bytes.decode("us-ascii")
        else:
            # Matrix code embedded in HHD_UC field
            matrix_data = _parse_embedded_matrix(hhduc_bytes)

    # Check for CHLGUC prefix (challenge with embedded data)
    if display_text.startswith("CHLGUC  "):
        char_count_str = display_text[8:12]
        if char_count_str.isdigit():
            offset = int(char_count_str, 10)
            embedded_data = display_text[12 : 12 + offset]
            display_text = display_text[12 + offset :]

            # Check if it's a base64-encoded PNG
            if embedded_data.startswith("iVBO"):
                matrix_data = ("image/png", b64decode(embedded_data))
            else:
                hhduc_data = embedded_data

    # Check for CHLGTEXT prefix
    if display_text.startswith("CHLGTEXT"):
        display_text = display_text[12:]

    # Sanitize HTML
    if structured:
        html_text = bleach.clean(
            display_text,
            tags=["br", "p", "b", "i", "u", "ul", "ol", "li"],
            attributes={},
        )
    else:
        html_text = bleach.clean(display_text, tags=[])

    return ParsedChallenge(
        raw_text=raw_text,
        display_text=display_text,
        html_text=html_text,
        hhduc_data=hhduc_data,
        matrix_data=matrix_data,
    )


def _parse_embedded_matrix(data: bytes) -> tuple[str, bytes] | None:
    """Parse matrix code from HHD_UC field with length-prefixed format."""
    if len(data) < 4:
        return None

    # Type length (2 bytes big-endian)
    type_len = data[0] * 256 + data[1]
    if len(data) < 2 + type_len + 2:
        return None

    type_data = data[2 : 2 + type_len]

    # Content length (2 bytes big-endian)
    content_offset = 2 + type_len
    content_len = data[content_offset] * 256 + data[content_offset + 1]

    if len(data) < content_offset + 2 + content_len:
        return None

    content_data = data[content_offset + 2 : content_offset + 2 + content_len]

    return (type_data.decode("us-ascii", "replace"), content_data)


class FinTSChallenge(Challenge):
    """
    FinTS-specific challenge wrapper.

    This provides a clean interface for challenge data without
    the full NeedTANResponse machinery.
    """

    def __init__(
        self,
        parsed: ParsedChallenge,
        decoupled: bool = False,
        task_reference: str | None = None,
    ) -> None:
        self._parsed = parsed
        self._decoupled = decoupled
        self._task_reference = task_reference

    @property
    def challenge_type(self) -> ChallengeType:
        if self._decoupled:
            return ChallengeType.DECOUPLED
        if self._parsed.matrix_data:
            mime = self._parsed.matrix_data[0]
            if mime and "png" in mime.lower():
                return ChallengeType.PHOTO_TAN
            return ChallengeType.MATRIX_CODE
        if self._parsed.hhduc_data:
            return ChallengeType.FLICKER
        return ChallengeType.TEXT

    @property
    def challenge_text(self) -> str | None:
        return self._parsed.display_text

    @property
    def challenge_html(self) -> str | None:
        return self._parsed.html_text

    @property
    def challenge_data(self) -> ChallengeData | None:
        if self._parsed.matrix_data:
            return ChallengeData(
                mime_type=self._parsed.matrix_data[0],
                data=self._parsed.matrix_data[1],
            )
        if self._parsed.hhduc_data:
            data = self._parsed.hhduc_data
            if isinstance(data, str):
                data = data.encode("us-ascii")
            return ChallengeData(mime_type="application/x-hhduc", data=data)
        return None

    @property
    def is_decoupled(self) -> bool:
        return self._decoupled

    @property
    def task_reference(self) -> str | None:
        """Task reference for TAN submission."""
        return self._task_reference

    def get_data(self) -> bytes:
        """Serialize for resumption - not implemented for wrapper."""
        raise NotImplementedError("Use NeedTANResponse for serializable challenges")


class NeedTANResponse(NeedRetryResponse, Challenge):
    """
    Response object signaling that the caller must supply a TAN.

    Implements the domain Challenge interface while adding FinTS-specific
    segment handling and serialization for dialog resumption.
    """

    challenge_raw = None
    challenge = None
    challenge_html = None
    challenge_hhduc = None
    challenge_matrix = None
    decoupled = None

    def __init__(
        self,
        command_seg,
        tan_request,
        resume_method=None,
        tan_request_structured=False,
        decoupled=False,
    ):
        self.command_seg = command_seg
        self.tan_request = tan_request
        self.tan_request_structured = tan_request_structured
        self.decoupled = decoupled
        if hasattr(resume_method, "__func__"):
            self.resume_method = resume_method.__func__.__name__
        else:
            self.resume_method = resume_method
        self._parse_tan_challenge()

    def __repr__(self):
        return (
            f"<{self.__class__.__name__}(command_seg={self.command_seg!r}, "
            f"tan_request={self.tan_request!r})>"
        )

    @classmethod
    def _from_data_v1(cls, data):
        if data["version"] == 1:
            segs = SegmentSequence(data["segments_bin"]).segments
            if "init_tan" in data:
                return cls(
                    None,
                    segs[0],
                    data["resume_method"],
                    data["tan_request_structured"],
                )
            else:
                return cls(
                    segs[0],
                    segs[1],
                    data["resume_method"],
                    data["tan_request_structured"],
                )
        raise Exception("Wrong blob data version")

    def get_data(self) -> bytes:
        """Return a compressed datablob representing this object."""
        if self.command_seg:
            data = {
                "_class_name": self.__class__.__name__,
                "version": 1,
                "segments_bin": SegmentSequence(
                    [self.command_seg, self.tan_request]
                ).render_bytes(),
                "resume_method": self.resume_method,
                "tan_request_structured": self.tan_request_structured,
            }
        else:
            data = {
                "_class_name": self.__class__.__name__,
                "version": 1,
                "init_tan": True,
                "segments_bin": SegmentSequence([self.tan_request]).render_bytes(),
                "resume_method": self.resume_method,
                "tan_request_structured": self.tan_request_structured,
            }
        return compress_datablob(DATA_BLOB_MAGIC_RETRY, 1, data)

    def _parse_tan_challenge(self):
        """Parse the TAN challenge from the request segment."""
        parsed = parse_tan_challenge(
            self.tan_request,
            structured=self.tan_request_structured,
        )
        self.challenge_raw = parsed.raw_text
        self.challenge = parsed.display_text
        self.challenge_html = parsed.html_text
        self.challenge_hhduc = parsed.hhduc_data
        self.challenge_matrix = parsed.matrix_data

    # --- Challenge interface implementation ---

    @property
    def challenge_type(self) -> ChallengeType:
        if self.decoupled:
            return ChallengeType.DECOUPLED
        if self.challenge_matrix:
            mime = self.challenge_matrix[0] if self.challenge_matrix else None
            if mime and "png" in mime.lower():
                return ChallengeType.PHOTO_TAN
            return ChallengeType.MATRIX_CODE
        if self.challenge_hhduc:
            return ChallengeType.FLICKER
        return ChallengeType.TEXT

    @property
    def challenge_text(self) -> str | None:
        return self.challenge

    @property
    def challenge_data(self) -> ChallengeData | None:
        if self.challenge_matrix:
            return ChallengeData(
                mime_type=self.challenge_matrix[0],
                data=self.challenge_matrix[1],
            )
        if self.challenge_hhduc:
            data = self.challenge_hhduc
            if isinstance(data, str):
                data = data.encode("us-ascii")
            return ChallengeData(mime_type="application/x-hhduc", data=data)
        return None

    @property
    def is_decoupled(self) -> bool:
        return bool(self.decoupled)


__all__ = [
    "FinTSChallenge",
    "NeedTANResponse",
    "ParsedChallenge",
    "parse_tan_challenge",
]
