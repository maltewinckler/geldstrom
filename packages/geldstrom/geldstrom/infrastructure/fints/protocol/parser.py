"""FinTS protocol parser and serializer (Pydantic-based)."""

from __future__ import annotations

import logging
import re
import types
from enum import Enum
from typing import Any, TypeVar

from pydantic import ValidationError

from . import segments as _segments  # noqa: F401  # Ensure segments are loaded
from .base import FinTSModel, FinTSSegment, SegmentHeader, SegmentSequence
from .tokenizer import ParserState, Token
from .types import (
    serialize_fints_bool,
    serialize_fints_date,
    serialize_fints_time,
)

T = TypeVar("T", bound=FinTSSegment)

logger = logging.getLogger(__name__)

# Track unknown segment types to avoid duplicate warnings
_unknown_segment_types: set[str] = set()


class FinTSParserError(ValueError):
    """Error raised when parser cannot parse data."""

    pass


class FinTSParser:
    """Converts FinTS wire bytes to Pydantic segment models.

    Unknown segments → GenericSegment (robust_mode=True) or error.
    Parameter segment (HI???S) parse errors → GenericSegment in robust_mode.
    Other model parse errors → always FinTSParserError (bug in model definition).
    """

    def __init__(self, robust_mode: bool = True):
        self.robust_mode = robust_mode

    def parse_message(self, data: bytes) -> SegmentSequence:
        raw_segments = self.explode_segments(data)

        # Parse each segment
        segments: list[FinTSSegment] = []
        for raw_seg in raw_segments:
            seg = self.parse_segment(raw_seg)
            if seg:
                segments.append(seg)

        return SegmentSequence(segments=segments)

    def parse_segment(self, raw_segment: list[Any]) -> FinTSSegment | None:
        if not raw_segment:
            return None

        # Parse header to determine segment type
        try:
            header = self._parse_header(raw_segment[0])
        except Exception as e:
            if self.robust_mode:
                logger.warning("Could not parse segment header: %s", e)
                return None
            raise FinTSParserError(f"Could not parse segment header: {e}") from e

        # Find segment class using auto-registration
        segment_class = FinTSSegment.get_segment_class(header.type, header.version)

        if not segment_class:
            if self.robust_mode:
                # Only log each unknown segment type once (at DEBUG level)
                key = f"{header.type}v{header.version}"
                if key not in _unknown_segment_types:
                    _unknown_segment_types.add(key)
                    logger.debug("Unknown segment type %s (using GenericSegment)", key)
                # Create a dynamic fallback segment that captures raw data
                return self._create_fallback_segment(header, raw_segment)
            raise FinTSParserError(
                f"Unknown segment type {header.type}v{header.version}"
            )

        # Parse segment
        try:
            return self._parse_segment_as_class(segment_class, raw_segment, header)
        except Exception as e:
            # Parameter segments (HI???S pattern) may have bank-specific variations
            # Allow these to fail gracefully in robust_mode
            is_parameter_segment = (
                len(header.type) == 6
                and header.type.startswith("HI")
                and header.type.endswith("S")
            )

            if self.robust_mode and is_parameter_segment:
                logger.debug(
                    "Parameter segment %sv%s has bank-specific format: %s",
                    header.type,
                    header.version,
                    e,
                )
                return self._create_fallback_segment(header, raw_segment)

            # For non-parameter segments, always fail (indicates bug in our model)
            raise FinTSParserError(
                f"Error parsing {header.type}v{header.version}: {e}"
            ) from e

    def _create_fallback_segment(
        self,
        header: SegmentHeader,
        raw_segment: list[Any],
    ) -> FinTSSegment:
        """Create a fallback segment for unknown segment types."""
        from .segments.params import GenericSegment

        # Create a minimal segment with just the header and raw data
        # Store raw data in the generic fields
        segment = GenericSegment(header=header)
        segment._raw_data = raw_segment  # Store raw data for debugging

        # Try to populate the generic data fields
        data_elements = raw_segment[1:]  # Skip header
        for i, value in enumerate(data_elements[:10]):  # Up to 10 fields
            field_name = f"data{i + 1}"
            if hasattr(segment, field_name):
                setattr(segment, field_name, value)

        # Store any remaining data
        if len(data_elements) > 10:
            segment.extra_data = data_elements[10:]

        return segment

    def _parse_header(self, raw_header: Any) -> SegmentHeader:
        """Parse segment header from raw data."""
        if isinstance(raw_header, (list, tuple)):
            # Header is [type, number, version, ref?]
            header_data = list(raw_header)
        else:
            # Single value - shouldn't happen for valid headers
            raise ValueError(f"Invalid header format: {raw_header}")

        if len(header_data) < 3:
            raise ValueError(f"Header too short: {header_data}")

        return SegmentHeader(
            type=header_data[0],
            number=int(header_data[1]) if header_data[1] else 0,
            version=int(header_data[2]) if header_data[2] else 0,
            reference=int(header_data[3])
            if len(header_data) > 3 and header_data[3]
            else None,
        )

    def _parse_segment_as_class(
        self,
        cls: type[T],
        raw_segment: list[Any],
        header: SegmentHeader,
    ) -> T:
        """Parse segment data into a specific class."""
        from .base import _extract_model_type

        data: dict[str, Any] = {"header": header}
        raw_data = raw_segment[1:]  # Skip header
        raw_index = 0

        for field_name, field_info in cls.model_fields.items():
            if field_name == "header" or raw_index >= len(raw_data):
                continue

            inner_type, is_list = self._unwrap_field_type(field_info.annotation)

            # List of DEGs: consume multiple raw values until next field
            if is_list and hasattr(inner_type, "from_wire_list"):
                items, raw_index = self._parse_deg_list(raw_data, raw_index, inner_type)
                if items:
                    data[field_name] = items
                continue

            # Single value
            raw_value = raw_data[raw_index]
            raw_index += 1

            if raw_value is None:
                continue

            # List of simple values (e.g., list[Language])
            if is_list:
                if isinstance(raw_value, list):
                    data[field_name] = raw_value
                else:
                    data[field_name] = [raw_value]
                continue

            # DEG field
            model_type = _extract_model_type(inner_type)
            if model_type and hasattr(model_type, "from_wire_list"):
                wire_list = raw_value if isinstance(raw_value, list) else [raw_value]
                data[field_name] = model_type.from_wire_list(wire_list)
            else:
                # Simple value - pass through
                data[field_name] = raw_value

        try:
            return cls.model_validate(data)
        except ValidationError as e:
            raise FinTSParserError(f"Validation failed for {cls.__name__}: {e}") from e

    def _unwrap_field_type(self, annotation: Any) -> tuple[Any, bool]:
        """Return (inner_type, is_list) for the given field annotation."""
        origin = getattr(annotation, "__origin__", None)

        # Handle X | None or Optional[X]
        if origin is types.UnionType or (
            hasattr(annotation, "__args__")
            and type(None) in getattr(annotation, "__args__", ())
        ):
            for arg in getattr(annotation, "__args__", ()):
                if arg is not type(None):
                    return self._unwrap_field_type(arg)

        # Handle list[X]
        if origin is list:
            args = getattr(annotation, "__args__", ())
            return (args[0] if args else Any, True)

        return (annotation, False)

    def _parse_deg_list(
        self,
        raw_data: list[Any],
        start_index: int,
        inner_type: type,
    ) -> tuple[list[Any], int]:
        """Consume list[DEG] entries until a non-list value; return (items, new_index)."""
        items = []
        index = start_index

        while index < len(raw_data):
            raw_value = raw_data[index]
            if isinstance(raw_value, list):
                items.append(inner_type.from_wire_list(raw_value))
                index += 1
            elif raw_value is None:
                # Skip empty slots
                index += 1
            else:
                # Non-list = next field; stop
                break

        return items, index

    @staticmethod
    def explode_segments(
        data: bytes, start: int = 0, end: int | None = None
    ) -> list[list[Any]]:
        """Explode raw bytes into a list of raw segments.

        Each segment is a list of DEGs (Data Element Groups).
        Each DEG is either a single value or a list of values.
        """
        segments: list[list[Any]] = []
        parser = ParserState(data, start, end)

        while parser.peek() != Token.EOF:
            segment: list[Any] = []

            while parser.peek() not in (Token.APOSTROPHE, Token.EOF):
                data_value: Any = None
                deg: list[Any] = []

                while parser.peek() in (Token.BINARY, Token.CHAR, Token.COLON):
                    if parser.peek() in (Token.BINARY, Token.CHAR):
                        data_value = parser.consume()
                    elif parser.peek() == Token.COLON:
                        deg.append(data_value)
                        data_value = None
                        parser.consume(Token.COLON)

                if data_value and deg:
                    deg.append(data_value)

                if deg:
                    data_value = deg

                segment.append(data_value)

                if parser.peek() == Token.PLUS:
                    parser.consume(Token.PLUS)

            parser.consume(Token.APOSTROPHE)
            segments.append(segment)

        parser.consume(Token.EOF)
        return segments


class FinTSSerializer:
    """Serializes Pydantic FinTS segments to wire-format bytes."""

    def serialize_message(
        self, message: SegmentSequence | list[FinTSSegment] | FinTSSegment
    ) -> bytes:
        if isinstance(message, FinTSSegment):
            message = SegmentSequence(segments=[message])
        elif isinstance(message, list):
            message = SegmentSequence(segments=message)

        result: list[list[Any]] = []
        for segment in message.segments:
            result.append(self.serialize_segment(segment))

        return self.implode_segments(result)

    def serialize_segment(self, segment: FinTSSegment) -> list[Any]:
        """Serialize a single segment to wire format data.

        Uses segment's to_wire_list() for custom formatting if overridden.
        """
        # Use to_wire_list() if overridden (e.g. HNHBK message_size)
        if (
            hasattr(segment, "to_wire_list")
            and type(segment).to_wire_list is not FinTSModel.to_wire_list
        ):
            return segment.to_wire_list()

        result: list[Any] = []

        for field_name in type(segment).model_fields:
            value = getattr(segment, field_name)

            if value is None:
                result.append(None)
                continue

            if isinstance(value, FinTSModel):
                # DEG - serialize recursively
                result.append(value.to_wire_list())
            elif isinstance(value, list):
                # Repeated field
                for item in value:
                    if isinstance(item, FinTSModel):
                        result.append(item.to_wire_list())
                    else:
                        result.append(self._serialize_value(item))
            else:
                result.append(self._serialize_value(value))

        return result

    def _serialize_value(self, value: Any) -> Any:
        import datetime

        if value is None:
            return None
        if isinstance(value, bool):
            return serialize_fints_bool(value)
        if isinstance(value, bytes):
            return value
        if isinstance(value, Enum):
            return str(value.value)
        # Let escape_value handle date/time formatting
        if isinstance(value, (datetime.date, datetime.time)):
            return value
        # Let escape_value handle numbers
        if isinstance(value, (int, float)):
            return value
        return str(value)

    @staticmethod
    def implode_segments(message: list[list[Any]]) -> bytes:
        """Combine serialized segments into wire format bytes."""
        level1: list[bytes] = []

        for segment in message:
            level2: list[bytes] = []
            for deg in segment:
                if isinstance(deg, (list, tuple)):
                    level2.append(FinTSSerializer._implode_deg(deg))
                else:
                    level2.append(FinTSSerializer.escape_value(deg))
            level1.append(b"+".join(level2))

        return b"'".join(level1) + b"'"

    @staticmethod
    def _implode_deg(deg: list | tuple) -> bytes:
        """Serialize a DEG (data element group) to bytes."""
        # Find highest non-empty index to trim trailing empty values
        highest_index = max(
            ((i + 1) for (i, e) in enumerate(deg) if e != b"" and e is not None),
            default=0,
        )

        parts: list[bytes] = []
        for de in deg[:highest_index]:
            if isinstance(de, (list, tuple)):
                # Nested DEG - serialize recursively
                parts.append(FinTSSerializer._implode_deg(de))
            else:
                parts.append(FinTSSerializer.escape_value(de))

        return b":".join(parts)

    @staticmethod
    def escape_value(val: Any) -> bytes:
        """Escape a value for wire format."""
        import datetime

        if isinstance(val, str):
            return re.sub(r"([+:'@?])", r"?\1", val).encode("iso-8859-1")
        elif isinstance(val, bytes):
            return f"@{len(val)}@".encode("us-ascii") + val
        elif val is None:
            return b""
        elif isinstance(val, bool):
            return serialize_fints_bool(val).encode("iso-8859-1")
        elif isinstance(val, datetime.date):
            return serialize_fints_date(val).encode("iso-8859-1")
        elif isinstance(val, datetime.time):
            return serialize_fints_time(val).encode("iso-8859-1")
        elif isinstance(val, (int, float)):
            return str(val).encode("iso-8859-1")
        elif isinstance(val, Enum):
            return str(val.value).encode("iso-8859-1")
        else:
            raise TypeError(
                f"Can only escape str, bytes, int, bool and None, got {type(val)}"
            )


def reset_unknown_segment_warnings() -> None:
    """Clear the cache of unknown segment types to re-enable duplicate warnings."""
    _unknown_segment_types.clear()


__all__ = [
    # Error
    "FinTSParserError",
    # Parser
    "FinTSParser",
    # Serializer
    "FinTSSerializer",
    # Utilities
    "reset_unknown_segment_warnings",
]
