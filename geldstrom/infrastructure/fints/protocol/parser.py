"""FinTS Protocol Parser - Pydantic-based segment parsing.

This module provides a parser that converts FinTS wire format into
Pydantic-based segment models.

Key Components:
- SegmentRegistry: Maps segment type+version to Pydantic model classes
- FinTSParser: Parses wire data into Pydantic segments
- FinTSSerializer: Serializes Pydantic segments back to wire format

Example:
    from geldstrom.infrastructure.fints.protocol.parser import (
        FinTSParser, SegmentRegistry
    )

    # Register custom segments
    registry = SegmentRegistry()
    registry.register(HISAL6)

    # Parse a message
    parser = FinTSParser(registry)
    segments = parser.parse_message(raw_bytes)
"""
from __future__ import annotations

import re
import warnings
from collections.abc import Iterator
from enum import Enum
from typing import Any, TypeVar, Union
import logging
import types

from pydantic import ValidationError

from .base import (
    FinTSDataElementGroup,
    FinTSModel,
    FinTSSegment,
    SegmentHeader,
    SegmentSequence,
)

# Import all segment classes for auto-registration
from .segments import (
    # Dialog segments
    HNHBK3, HNHBS1,
    HIRMG2, HIRMS2,
    HKSYN3, HISYN4,
    HKEND1,
    # Message security segments
    HNVSK3, HNVSD1,
    HNSHK4, HNSHA2,
    # Auth segments
    HKIDN2, HKVVB3,
    HKTAN2, HKTAN6, HKTAN7,
    HITAN6, HITAN7,
    HKTAB4, HKTAB5,
    HITAB4, HITAB5,
    # Bank parameter segments
    HIBPA3,
    HIUPA4, HIUPD6,
    HKKOM4, HIKOM4,
    # PIN/TAN parameter segments
    HIPINS1,
    HITANS1, HITANS2, HITANS3, HITANS4, HITANS5, HITANS6, HITANS7,
    # Balance segments
    HKSAL5, HKSAL6, HKSAL7,
    HISAL5, HISAL6, HISAL7,
    # Account segments
    HKSPA1, HISPA1,
    # Transaction segments
    HKKAZ5, HKKAZ6, HKKAZ7,
    HIKAZ5, HIKAZ6, HIKAZ7,
    HKCAZ1, HICAZ1,
    # Statement segments
    HKEKA3, HKEKA4, HKEKA5,
    HIEKA3, HIEKA4, HIEKA5,
    HKKAU1, HKKAU2,
    HIKAU1, HIKAU2,
    # Transfer segments
    HKCCS1, HKIPZ1,
    HKCCM1, HKIPM1,
    HICCMS1,
    # Depot segments
    HKWPD5, HKWPD6,
    HIWPD5, HIWPD6,
    # Journal segments
    HKPRO3, HKPRO4,
    HIPRO3, HIPRO4,
    HIPROS3, HIPROS4,
    # Informational segments
    HIAZSS1,
    HIVISS1,
    # Parameter segments
    HISPAS1, HISPAS2, HISPAS3,
    HISALS4, HISALS5, HISALS6, HISALS7,
    HIKAZS4, HIKAZS5, HIKAZS6, HIKAZS7,
    HIEKAS3, HIEKAS4, HIEKAS5,
    HISHV3,
    HICCSS1_PARAMS,
    HIDSCS1, HIBSES1, HIDSES1, HIDMES1, HIBMES1,
    HIPAES1, HIPSPS1, HIQTGS1,
    HICSAS1, HICSBS1, HICSLS1, HICSES1,
    HICDBS1, HICDLS1, HICDNS1,
    # Bank-specific generic segments
    HIDSBS1, HICUBS1, HICUMS1, HICDES1, HIDSWS1,
    HIECAS1, HIDBSS1, HIBBSS1, HIDMBS1, HIBMBS1,
    HICMBS1, HICMES1, HICMLS1,
    HIWPDS6, HIWPDS7,
    HIIPZS1, HIIPMS1,
    HICAZS1,
    HIKAUS1, HIKAUS2,
    HIPROS5,
    HITABS4, HITABS5,
    # Version 2 and additional
    HIBMES2, HIBSES2, HIDSES2, HIDMES2,
    HIWDUS5, HIKIFS7, HIBAZS1, HIZDFS1, HIDVKS2,
    HIKOMS4, HIDSWS2,
    HICCMS1_PARAMS, HICCMS2, HIDSCS2,
    HIDMCS1, HIDMCS2,
    HIDBSS2, HIBBSS2,
)


T = TypeVar("T", bound=FinTSSegment)

logger = logging.getLogger(__name__)


class FinTSParserWarning(UserWarning):
    """Warning raised when parser encounters non-fatal errors."""
    pass


class FinTSParserError(ValueError):
    """Error raised when parser cannot parse data."""
    pass


# =============================================================================
# Tokenizer (reused from legacy parser)
# =============================================================================


TOKEN_RE = re.compile(rb"""
                        ^(?:  (?: \? (?P<ECHAR>.) )
                            | (?P<CHAR>[^?:+@']+)
                            | (?P<TOK>[+:'])
                            | (?: @ (?P<BINLEN>[0-9]+) @ )
                         )""", re.X | re.S)


class Token(Enum):
    """Token types in FinTS wire format."""
    EOF = 'eof'
    CHAR = 'char'
    BINARY = 'bin'
    PLUS = '+'
    COLON = ':'
    APOSTROPHE = "'"


class ParserState:
    """Stateful tokenizer for FinTS wire format."""

    def __init__(self, data: bytes, start: int = 0, end: int | None = None, encoding: str = 'iso-8859-1'):
        self._token: Token | None = None
        self._value: Any = None
        self._encoding = encoding
        self._tokenizer = iter(self._tokenize(data, start, end or len(data), encoding))

    def peek(self) -> Token:
        """Look at next token without consuming it."""
        if not self._token:
            self._token, self._value = next(self._tokenizer)
        return self._token

    def consume(self, token: Token | None = None) -> Any:
        """Consume and return the next token value."""
        self.peek()
        if token and token != self._token:
            raise ValueError(f"Expected {token}, got {self._token}")
        self._token = None
        return self._value

    @staticmethod
    def _tokenize(data: bytes, start: int, end: int, encoding: str) -> Iterator[tuple[Token, Any]]:
        """Tokenize FinTS wire data."""
        pos = start
        unclaimed: list[bytes] = []
        last_was: Token | None = None

        while pos < end:
            match = TOKEN_RE.match(data[pos:end])
            if match:
                pos += match.end()
                d = match.groupdict()
                if d['ECHAR'] is not None:
                    unclaimed.append(d['ECHAR'])
                elif d['CHAR'] is not None:
                    unclaimed.append(d['CHAR'])
                else:
                    if unclaimed:
                        if last_was in (Token.BINARY, Token.CHAR):
                            raise ValueError("Consecutive char/binary tokens")
                        yield Token.CHAR, b''.join(unclaimed).decode(encoding)
                        unclaimed.clear()
                        last_was = Token.CHAR

                    if d['TOK'] is not None:
                        token = Token(d['TOK'].decode('us-ascii'))
                        yield token, d['TOK']
                        last_was = token
                    elif d['BINLEN'] is not None:
                        blen = int(d['BINLEN'].decode('us-ascii'), 10)
                        if last_was in (Token.BINARY, Token.CHAR):
                            raise ValueError("Consecutive char/binary tokens")
                        yield Token.BINARY, data[pos:pos+blen]
                        pos += blen
                        last_was = Token.BINARY
                    else:
                        raise ValueError("Unknown token type")
            else:
                raise ValueError(f"Cannot tokenize at position {pos}")

        if unclaimed:
            if last_was in (Token.BINARY, Token.CHAR):
                raise ValueError("Trailing unclaimed data")
            yield Token.CHAR, b''.join(unclaimed).decode(encoding)

        yield Token.EOF, b''


# =============================================================================
# Segment Registry
# =============================================================================


class SegmentRegistry:
    """Registry mapping segment type+version to Pydantic model classes.

    The registry automatically discovers and registers all FinTSSegment
    subclasses that have SEGMENT_TYPE and SEGMENT_VERSION defined.

    Example:
        registry = SegmentRegistry()

        # Get class for parsing
        cls = registry.get("HISAL", 6)  # Returns HISAL6

        # Register custom segment
        registry.register(MyCustomSegment)
    """

    def __init__(self, auto_register: bool = True):
        self._registry: dict[tuple[str, int], type[FinTSSegment]] = {}

        if auto_register:
            self._auto_register()

    def _auto_register(self) -> None:
        """Auto-register all known segment classes."""
        # All imported segment classes
        segment_classes = [
            # Dialog
            HNHBK3, HNHBS1,
            HIRMG2, HIRMS2,
            HKSYN3, HISYN4,
            HKEND1,
            # Message security
            HNVSK3, HNVSD1,
            HNSHK4, HNSHA2,
            # Auth
            HKIDN2, HKVVB3,
            HKTAN2, HKTAN6, HKTAN7,
            HITAN6, HITAN7,
            HKTAB4, HKTAB5,
            HITAB4, HITAB5,
            # Bank parameters
            HIBPA3,
            HIUPA4, HIUPD6,
            HKKOM4, HIKOM4,
            # PIN/TAN parameters
            HIPINS1,
            HITANS1, HITANS2, HITANS3, HITANS4, HITANS5, HITANS6, HITANS7,
            # Balance
            HKSAL5, HKSAL6, HKSAL7,
            HISAL5, HISAL6, HISAL7,
            # Account
            HKSPA1, HISPA1,
            # Transaction
            HKKAZ5, HKKAZ6, HKKAZ7,
            HIKAZ5, HIKAZ6, HIKAZ7,
            HKCAZ1, HICAZ1,
            # Statement
            HKEKA3, HKEKA4, HKEKA5,
            HIEKA3, HIEKA4, HIEKA5,
            HKKAU1, HKKAU2,
            HIKAU1, HIKAU2,
            # Transfer
            HKCCS1, HKIPZ1,
            HKCCM1, HKIPM1,
            HICCMS1,
            # Depot
            HKWPD5, HKWPD6,
            HIWPD5, HIWPD6,
            # Journal
            HKPRO3, HKPRO4,
            HIPRO3, HIPRO4,
            HIPROS3, HIPROS4,
            # Informational
            HIAZSS1,
            HIVISS1,
            # Parameter segments
            HISPAS1, HISPAS2, HISPAS3,
            HISALS4, HISALS5, HISALS6, HISALS7,
            HIKAZS4, HIKAZS5, HIKAZS6, HIKAZS7,
            HIEKAS3, HIEKAS4, HIEKAS5,
            HISHV3,
            HICCSS1_PARAMS,
            HIDSCS1, HIBSES1, HIDSES1, HIDMES1, HIBMES1,
            HIPAES1, HIPSPS1, HIQTGS1,
            HICSAS1, HICSBS1, HICSLS1, HICSES1,
            HICDBS1, HICDLS1, HICDNS1,
            # Bank-specific generic segments
            HIDSBS1, HICUBS1, HICUMS1, HICDES1, HIDSWS1,
            HIECAS1, HIDBSS1, HIBBSS1, HIDMBS1, HIBMBS1,
            HICMBS1, HICMES1, HICMLS1,
            HIWPDS6, HIWPDS7,
            HIIPZS1, HIIPMS1,
            HICAZS1,
            HIKAUS1, HIKAUS2,
            HIPROS5,
            HITABS4, HITABS5,
            # Version 2 and additional
            HIBMES2, HIBSES2, HIDSES2, HIDMES2,
            HIWDUS5, HIKIFS7, HIBAZS1, HIZDFS1, HIDVKS2,
            HIKOMS4, HIDSWS2,
            HICCMS1_PARAMS, HICCMS2, HIDSCS2,
            HIDMCS1, HIDMCS2,
            HIDBSS2, HIBBSS2,
        ]

        for cls in segment_classes:
            self.register(cls)

    def register(self, cls: type[FinTSSegment]) -> None:
        """Register a segment class."""
        segment_type = cls.SEGMENT_TYPE
        version = cls.SEGMENT_VERSION

        if not segment_type or not version:
            raise ValueError(f"Segment class {cls.__name__} must have SEGMENT_TYPE and SEGMENT_VERSION")

        key = (segment_type, version)
        self._registry[key] = cls

    def get(self, segment_type: str, version: int) -> type[FinTSSegment] | None:
        """Get segment class by type and version."""
        return self._registry.get((segment_type, version))

    def get_versions(self, segment_type: str) -> list[int]:
        """Get all registered versions for a segment type."""
        return sorted(v for t, v in self._registry if t == segment_type)

    def get_highest_version(self, segment_type: str) -> type[FinTSSegment] | None:
        """Get segment class with highest version."""
        versions = self.get_versions(segment_type)
        if versions:
            return self.get(segment_type, versions[-1])
        return None

    @property
    def registered_types(self) -> set[str]:
        """Get all registered segment types."""
        return {t for t, _ in self._registry}

    def __contains__(self, key: tuple[str, int]) -> bool:
        return key in self._registry

    def __len__(self) -> int:
        return len(self._registry)


# Default registry instance
_default_registry = SegmentRegistry()


def get_default_registry() -> SegmentRegistry:
    """Get the default segment registry."""
    return _default_registry


# =============================================================================
# Parser
# =============================================================================


class FinTSParser:
    """Parser for FinTS wire format into Pydantic models.

    The parser converts raw FinTS bytes into structured Pydantic segment
    models, providing type safety and validation.

    Example:
        parser = FinTSParser()

        # Parse a full message
        segments = parser.parse_message(raw_bytes)

        # Access parsed segments
        for seg in segments.find_segments("HISAL"):
            print(f"Balance: {seg.balance_booked.signed_amount}")
    """

    def __init__(
        self,
        registry: SegmentRegistry | None = None,
        robust_mode: bool = True,
    ):
        """Initialize parser.

        Args:
            registry: Segment registry (uses default if None)
            robust_mode: If True, parsing errors become warnings
        """
        self.registry = registry or get_default_registry()
        self.robust_mode = robust_mode

    def parse_message(self, data: bytes) -> SegmentSequence:
        """Parse a FinTS message into a SegmentSequence.

        Args:
            data: Raw FinTS message bytes

        Returns:
            SegmentSequence containing parsed segments
        """
        # Explode into raw segments
        raw_segments = self.explode_segments(data)

        # Parse each segment
        segments: list[FinTSSegment] = []
        for raw_seg in raw_segments:
            seg = self.parse_segment(raw_seg)
            if seg:
                segments.append(seg)

        return SegmentSequence(segments=segments)

    def parse_segment(self, raw_segment: list[Any]) -> FinTSSegment | None:
        """Parse a single raw segment into a Pydantic model.

        Args:
            raw_segment: Exploded segment data (list of DEGs)

        Returns:
            Parsed segment or None if parsing failed
        """
        if not raw_segment:
            return None

        # Parse header to determine segment type
        try:
            header = self._parse_header(raw_segment[0])
        except Exception as e:
            if self.robust_mode:
                warnings.warn(f"Could not parse segment header: {e}", FinTSParserWarning)
                return None
            raise FinTSParserError(f"Could not parse segment header: {e}") from e

        # Find segment class
        segment_class = self.registry.get(header.type, header.version)

        if not segment_class:
            if self.robust_mode:
                warnings.warn(
                    f"Unknown segment type {header.type}v{header.version}",
                    FinTSParserWarning
                )
                # Create a dynamic fallback segment that captures raw data
                return self._create_fallback_segment(header, raw_segment)
            raise FinTSParserError(f"Unknown segment type {header.type}v{header.version}")

        # Parse segment
        try:
            return self._parse_segment_as_class(segment_class, raw_segment, header)
        except Exception as e:
            if self.robust_mode:
                warnings.warn(
                    f"Error parsing {header.type}v{header.version}: {e}",
                    FinTSParserWarning
                )
                return None
            raise FinTSParserError(f"Error parsing {header.type}v{header.version}: {e}") from e

    def _create_fallback_segment(
        self,
        header: SegmentHeader,
        raw_segment: list[Any],
    ) -> FinTSSegment:
        """Create a fallback segment for unknown segment types.

        This allows the parser to continue processing even when
        encountering unknown bank-specific segments.
        """
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
            reference=int(header_data[3]) if len(header_data) > 3 and header_data[3] else None,
        )

    def _parse_segment_as_class(
        self,
        cls: type[T],
        raw_segment: list[Any],
        header: SegmentHeader,
    ) -> T:
        """Parse segment data into a specific class.

        In FinTS wire format, each segment is a list of DEGs (Data Element Groups).
        Each DEG can be:
        - A simple value (string, number, etc.)
        - A list of values (multiple elements in a DEG, separated by ':')

        The parser creates structured data where nested DEGs are already lists.
        """
        from .base import _is_fints_model_type, _extract_model_type

        # Prepare data for Pydantic model
        data = {
            "header": header,
        }

        # Get field info from model
        field_names = list(cls.model_fields.keys())
        field_names.remove("header")  # Already handled

        # Remaining data after header - each element is a DEG
        raw_data = list(raw_segment[1:])  # Skip header
        raw_index = 0

        for field_name in field_names:
            if raw_index >= len(raw_data):
                # No more data - remaining fields use defaults
                break

            field_info = cls.model_fields[field_name]
            annotation = field_info.annotation
            origin = getattr(annotation, "__origin__", None)

            actual_annotation = annotation
            if origin is Union or isinstance(annotation, types.UnionType):
                args = getattr(annotation, "__args__", ())
                for arg in args:
                    if arg is not type(None):
                        actual_annotation = arg
                        origin = getattr(actual_annotation, "__origin__", None)
                        break

            # Check if this is a list field with a DEG type
            if origin is list:
                args = getattr(actual_annotation, "__args__", ())
                if args:
                    inner_type = args[0]
                    # Check if inner type is a DEG
                    if hasattr(inner_type, "from_wire_list"):
                        # Collect remaining list items for this field
                        # Stop when we encounter a non-list value (next field)
                        list_values = []
                        while raw_index < len(raw_data):
                            raw_value = raw_data[raw_index]
                            # Only consume actual list values as list items
                            # None values are empty slots - skip them
                            # Non-list values indicate we've hit the next field
                            if isinstance(raw_value, list):
                                raw_index += 1
                                item = inner_type.from_wire_list(raw_value)
                                list_values.append(item)
                            elif raw_value is None:
                                # Skip None values (empty slots in FinTS)
                                raw_index += 1
                            else:
                                # Non-list, non-None value means we've hit the next field
                                # Don't consume it - leave for next iteration
                                break
                        if list_values:
                            data[field_name] = list_values
                        continue

            # Get the raw value for this field
            raw_value = raw_data[raw_index]
            raw_index += 1

            # Check for nested DEG type
            if _is_fints_model_type(actual_annotation):
                model_type = _extract_model_type(actual_annotation)
                if model_type is not None:
                    if isinstance(raw_value, list):
                        # DEG is a list - pass to from_wire_list
                        parsed_value = model_type.from_wire_list(raw_value)
                    elif raw_value is not None:
                        # Single value - wrap in list for from_wire_list
                        parsed_value = model_type.from_wire_list([raw_value])
                    else:
                        parsed_value = None

                    if parsed_value is not None:
                        data[field_name] = parsed_value
                    continue

            # Regular field - parse the single value
            parsed_value = self._parse_field_value(raw_value, field_info)
            if parsed_value is not None or not field_info.is_required():
                data[field_name] = parsed_value

        # Create and validate model
        try:
            return cls.model_validate(data)
        except ValidationError as e:
            raise FinTSParserError(f"Validation failed for {cls.__name__}: {e}") from e

    def _parse_field_value(self, raw_value: Any, field_info: Any) -> Any:
        """Parse a raw value according to field info.

        This handles:
        - None/empty values
        - Lists (repeated fields)
        - DEGs (nested data element groups)
        - Simple data elements
        """
        if raw_value is None:
            return None

        # Check if this is a list field
        annotation = field_info.annotation
        origin = getattr(annotation, "__origin__", None)

        if origin is list:
            # Handle list fields
            if isinstance(raw_value, list):
                args = getattr(annotation, "__args__", ())
                if args:
                    inner_type = args[0]
                    if hasattr(inner_type, "from_wire_list"):
                        return [inner_type.from_wire_list(v) if isinstance(v, list) else v for v in raw_value]
                return raw_value
            return [raw_value]

        # Check if annotation is a DEG
        actual_type = annotation
        if origin is type(None) or (hasattr(annotation, "__args__") and type(None) in getattr(annotation, "__args__", ())):
            # Handle Optional[X] -> get X
            args = getattr(annotation, "__args__", ())
            for arg in args:
                if arg is not type(None):
                    actual_type = arg
                    break

        if hasattr(actual_type, "from_wire_list") and isinstance(raw_value, list):
            return actual_type.from_wire_list(raw_value)

        return raw_value

    @staticmethod
    def explode_segments(data: bytes, start: int = 0, end: int | None = None) -> list[list[Any]]:
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


# =============================================================================
# Serializer
# =============================================================================


class FinTSSerializer:
    """Serializer for Pydantic segments to FinTS wire format.

    Example:
        serializer = FinTSSerializer()
        raw_bytes = serializer.serialize_message(segment_sequence)
    """

    def serialize_message(self, message: SegmentSequence | list[FinTSSegment] | FinTSSegment) -> bytes:
        """Serialize segments to FinTS wire format.

        Args:
            message: Segments to serialize

        Returns:
            Wire format bytes
        """
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

        Uses the segment's to_wire_list() method if available for custom formatting.
        """
        # Use to_wire_list() if available (handles special formatting like HNHBK message_size)
        if hasattr(segment, 'to_wire_list') and type(segment).to_wire_list is not FinTSModel.to_wire_list:
            return segment.to_wire_list()

        result: list[Any] = []

        for field_name in type(segment).model_fields.keys():
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
        """Serialize a single value to wire format.

        Returns the value as-is for types that escape_value handles specially
        (date, time, int, bytes), or converts to string for others.
        """
        import datetime

        if value is None:
            return None
        if isinstance(value, bool):
            return "J" if value else "N"
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
        """Serialize a DEG (data element group) to bytes.

        Handles nested DEGs recursively.
        """
        # Find highest non-empty index to trim trailing empty values
        highest_index = max(
            ((i + 1) for (i, e) in enumerate(deg) if e != b'' and e is not None),
            default=0
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
            return re.sub(r"([+:'@?])", r"?\1", val).encode('iso-8859-1')
        elif isinstance(val, bytes):
            return f"@{len(val)}@".encode('us-ascii') + val
        elif val is None:
            return b''
        elif isinstance(val, bool):
            return b'J' if val else b'N'
        elif isinstance(val, datetime.date):
            # FinTS date format: YYYYMMDD
            return val.strftime('%Y%m%d').encode('iso-8859-1')
        elif isinstance(val, datetime.time):
            # FinTS time format: HHMMSS
            return val.strftime('%H%M%S').encode('iso-8859-1')
        elif isinstance(val, (int, float)):
            return str(val).encode('iso-8859-1')
        elif isinstance(val, Enum):
            return str(val.value).encode('iso-8859-1')
        else:
            raise TypeError(f"Can only escape str, bytes, int, bool and None, got {type(val)}")


__all__ = [
    # Errors
    "FinTSParserError",
    "FinTSParserWarning",
    # Tokenizer
    "Token",
    "ParserState",
    # Registry
    "SegmentRegistry",
    "get_default_registry",
    # Parser
    "FinTSParser",
    # Serializer
    "FinTSSerializer",
]

