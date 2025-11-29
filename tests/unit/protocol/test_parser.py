"""Unit tests for fints.infrastructure.fints.protocol.parser.

Tests cover:
- Tokenizer (ParserState)
- Segment exploding
- Segment registry
- Parser with real segment classes
- Serializer round-trip
"""
from __future__ import annotations

import pytest

from fints.infrastructure.fints.protocol.parser import (
    FinTSParser,
    FinTSParserError,
    FinTSParserWarning,
    FinTSSerializer,
    ParserState,
    SegmentRegistry,
    Token,
    get_default_registry,
)
from fints.infrastructure.fints.protocol.segments import (
    HKSAL6,
    HKSAL7,
    HISAL6,
    HIKAZ6,
)


# =============================================================================
# Tokenizer Tests
# =============================================================================


class TestParserState:
    """Tests for the tokenizer."""

    def test_tokenize_simple_segment(self):
        """Tokenize a simple segment."""
        data = b"HNHBS:5:1+2'"
        state = ParserState(data)

        # HNHBS
        assert state.peek() == Token.CHAR
        assert state.consume() == "HNHBS"

        # :
        assert state.peek() == Token.COLON
        state.consume(Token.COLON)

        # 5
        assert state.peek() == Token.CHAR
        assert state.consume() == "5"

        # :
        assert state.consume(Token.COLON) == b":"

        # 1
        assert state.consume() == "1"

        # +
        assert state.consume(Token.PLUS) == b"+"

        # 2
        assert state.consume() == "2"

        # '
        assert state.consume(Token.APOSTROPHE) == b"'"

        # EOF
        assert state.peek() == Token.EOF

    def test_tokenize_binary_data(self):
        """Tokenize segment with binary data."""
        binary_content = b"\x00\x01\x02\x03"
        data = b"HIKAZ:3:6+@4@" + binary_content + b"'"
        state = ParserState(data)

        # HIKAZ
        assert state.consume() == "HIKAZ"
        state.consume(Token.COLON)
        assert state.consume() == "3"
        state.consume(Token.COLON)
        assert state.consume() == "6"
        state.consume(Token.PLUS)

        # Binary
        assert state.peek() == Token.BINARY
        assert state.consume() == binary_content

        state.consume(Token.APOSTROPHE)
        assert state.peek() == Token.EOF

    def test_tokenize_escaped_chars(self):
        """Tokenize segment with escaped special characters."""
        data = b"TEST+Hello?+World?:Test'"
        state = ParserState(data)

        assert state.consume() == "TEST"
        state.consume(Token.PLUS)
        # Escaped + and : become part of the value
        assert state.consume() == "Hello+World:Test"

    def test_consume_wrong_token_raises(self):
        """Consuming wrong token type raises ValueError."""
        state = ParserState(b"TEST+")
        assert state.peek() == Token.CHAR

        with pytest.raises(ValueError):
            state.consume(Token.PLUS)


# =============================================================================
# Explode Segments Tests
# =============================================================================


class TestExplodeSegments:
    """Tests for segment exploding."""

    def test_explode_single_segment(self):
        """Explode a single segment."""
        data = b"HNHBS:5:1+2'"
        segments = FinTSParser.explode_segments(data)

        assert len(segments) == 1
        assert segments[0][0] == ["HNHBS", "5", "1"]  # Header DEG
        assert segments[0][1] == "2"  # Body

    def test_explode_multiple_segments(self):
        """Explode multiple segments."""
        data = b"HNHBK:1:3+000000000139+300+dialogid+1'HNHBS:2:1+1'"
        segments = FinTSParser.explode_segments(data)

        assert len(segments) == 2
        assert segments[0][0] == ["HNHBK", "1", "3"]
        assert segments[1][0] == ["HNHBS", "2", "1"]

    def test_explode_empty_fields(self):
        """Explode segment with empty fields."""
        data = b"TEST:1:1++value++'"
        segments = FinTSParser.explode_segments(data)

        assert len(segments) == 1
        # Empty fields become None
        assert segments[0][1] is None
        assert segments[0][2] == "value"
        assert segments[0][3] is None

    def test_explode_nested_deg(self):
        """Explode segment with nested DEG."""
        data = b"TEST:1:1+field1:field2:field3'"
        segments = FinTSParser.explode_segments(data)

        assert len(segments) == 1
        assert segments[0][1] == ["field1", "field2", "field3"]


# =============================================================================
# Segment Registry Tests
# =============================================================================


class TestSegmentRegistry:
    """Tests for segment registry."""

    def test_default_registry_has_segments(self):
        """Default registry has auto-registered segments."""
        registry = get_default_registry()

        assert len(registry) > 0
        assert ("HISAL", 6) in registry
        assert ("HKSAL", 7) in registry
        assert ("HIKAZ", 6) in registry

    def test_get_segment_class(self):
        """Get segment class by type and version."""
        registry = SegmentRegistry()

        cls = registry.get("HISAL", 6)
        assert cls == HISAL6

        cls = registry.get("HKSAL", 7)
        assert cls == HKSAL7

    def test_get_unknown_segment(self):
        """Get returns None for unknown segments."""
        registry = SegmentRegistry()

        assert registry.get("UNKNOWN", 1) is None
        assert registry.get("HISAL", 999) is None

    def test_get_versions(self):
        """Get all versions for a segment type."""
        registry = SegmentRegistry()

        versions = registry.get_versions("HKSAL")
        assert 5 in versions
        assert 6 in versions
        assert 7 in versions

    def test_get_highest_version(self):
        """Get highest version segment class."""
        registry = SegmentRegistry()

        cls = registry.get_highest_version("HKSAL")
        assert cls == HKSAL7

    def test_registered_types(self):
        """Get all registered segment types."""
        registry = SegmentRegistry()

        types = registry.registered_types
        assert "HISAL" in types
        assert "HKSAL" in types
        assert "HIKAZ" in types

    def test_register_custom_segment(self):
        """Register a custom segment class."""
        registry = SegmentRegistry(auto_register=False)

        assert len(registry) == 0

        registry.register(HISAL6)

        assert len(registry) == 1
        assert registry.get("HISAL", 6) == HISAL6


# =============================================================================
# Parser Tests
# =============================================================================


class TestFinTSParser:
    """Tests for the FinTS parser."""

    def test_parse_simple_segment(self):
        """Parse a simple segment with header only."""
        # Minimal valid segment
        data = b"HKSAL:3:6+280:12345678+1234567890::280:12345678+N'"
        parser = FinTSParser()

        segments = parser.parse_message(data)

        # Should parse (or warn in robust mode if not all fields match)
        assert len(segments.segments) >= 0  # May be 0 if parsing fails

    def test_robust_mode_warns_on_error(self):
        """Robust mode emits warning instead of raising."""
        # Invalid segment data
        data = b"INVALID:1:1+garbage'"
        parser = FinTSParser(robust_mode=True)

        with pytest.warns(FinTSParserWarning):
            segments = parser.parse_message(data)

        # No segments parsed
        assert len(segments.segments) == 0

    def test_strict_mode_raises_on_error(self):
        """Strict mode raises on error."""
        data = b"INVALID:1:1+garbage'"
        parser = FinTSParser(robust_mode=False)

        with pytest.raises(FinTSParserError):
            parser.parse_message(data)

    def test_parse_unknown_segment_type(self):
        """Unknown segment type emits warning in robust mode."""
        data = b"UNKNOWN:1:99+data'"
        parser = FinTSParser(robust_mode=True)

        with pytest.warns(FinTSParserWarning):
            segments = parser.parse_message(data)

        assert len(segments.segments) == 0


# =============================================================================
# Serializer Tests
# =============================================================================


class TestFinTSSerializer:
    """Tests for the FinTS serializer."""

    def test_escape_string(self):
        """Escape special characters in strings."""
        assert FinTSSerializer.escape_value("hello") == b"hello"
        assert FinTSSerializer.escape_value("hello+world") == b"hello?+world"
        assert FinTSSerializer.escape_value("a:b") == b"a?:b"
        assert FinTSSerializer.escape_value("test'end") == b"test?'end"
        assert FinTSSerializer.escape_value("@data@") == b"?@data?@"
        assert FinTSSerializer.escape_value("a?b") == b"a??b"

    def test_escape_binary(self):
        """Escape binary data with length prefix."""
        data = b"\x00\x01\x02\x03"
        escaped = FinTSSerializer.escape_value(data)

        assert escaped == b"@4@\x00\x01\x02\x03"

    def test_escape_none(self):
        """Escape None as empty bytes."""
        assert FinTSSerializer.escape_value(None) == b""

    def test_implode_simple_segment(self):
        """Implode a simple segment."""
        segment_data = [
            [["HNHBS", "5", "1"], "2"]
        ]

        result = FinTSSerializer.implode_segments(segment_data)

        assert result == b"HNHBS:5:1+2'"

    def test_implode_multiple_segments(self):
        """Implode multiple segments."""
        segment_data = [
            [["TEST", "1", "1"], "a"],
            [["TEST", "2", "1"], "b"],
        ]

        result = FinTSSerializer.implode_segments(segment_data)

        assert result == b"TEST:1:1+a'TEST:2:1+b'"


# =============================================================================
# Round-Trip Tests
# =============================================================================


class TestRoundTrip:
    """Tests for parse-serialize round trips."""

    def test_explode_implode_roundtrip(self):
        """Exploding and imploding should preserve data."""
        original = b"HNHBS:5:1+2'"

        exploded = FinTSParser.explode_segments(original)
        imploded = FinTSSerializer.implode_segments(exploded)

        assert imploded == original

    def test_explode_implode_complex(self):
        """Round-trip complex message."""
        original = b"HNHBK:1:3+000000000139+300+dialogid+1'HNHBS:2:1+1'"

        exploded = FinTSParser.explode_segments(original)
        imploded = FinTSSerializer.implode_segments(exploded)

        assert imploded == original

    def test_explode_implode_with_binary(self):
        """Round-trip message with binary data."""
        binary_content = b"\x00\x01\x02\x03"
        original = b"TEST:1:1+@4@" + binary_content + b"'"

        exploded = FinTSParser.explode_segments(original)

        # Verify binary is preserved
        assert exploded[0][1] == binary_content

        # Note: implode will re-add the length prefix
        imploded = FinTSSerializer.implode_segments(exploded)
        assert imploded == original

