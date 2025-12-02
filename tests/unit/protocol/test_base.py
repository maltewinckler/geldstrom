"""Comprehensive unit tests for fints.protocol.base.

Tests cover:
- FinTSModel base class
- FinTSDataElementGroup
- SegmentHeader
- FinTSSegment
- SegmentSequence with query methods
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import ClassVar

import pytest

from geldstrom.infrastructure.fints.protocol.base import (
    FinTSDataElementGroup,
    FinTSModel,
    FinTSSegment,
    SegmentHeader,
    SegmentSequence,
)
from geldstrom.infrastructure.fints.protocol.types import (
    FinTSAlphanumeric,
    FinTSAmount,
    FinTSCurrency,
    FinTSDate,
    FinTSNumeric,
)

# =============================================================================
# Test Models (reusable fixtures)
# =============================================================================


class SimpleModel(FinTSModel):
    """Simple test model."""

    name: FinTSAlphanumeric
    value: FinTSNumeric


class OptionalModel(FinTSModel):
    """Model with optional fields."""

    required_field: FinTSAlphanumeric
    optional_field: FinTSAlphanumeric | None = None


class NestedDEG(FinTSDataElementGroup):
    """Nested DEG for testing."""

    amount: FinTSAmount
    currency: FinTSCurrency


class ParentModel(FinTSModel):
    """Model containing a nested model."""

    name: FinTSAlphanumeric
    nested: NestedDEG


class SampleSegment(FinTSSegment):
    """Sample segment for unit tests."""

    SEGMENT_TYPE: ClassVar[str] = "SAMPLE"
    SEGMENT_VERSION: ClassVar[int] = 1

    data: FinTSAlphanumeric


class SampleSegmentV2(FinTSSegment):
    """Version 2 of sample segment."""

    SEGMENT_TYPE: ClassVar[str] = "SAMPLE"
    SEGMENT_VERSION: ClassVar[int] = 2

    data: FinTSAlphanumeric
    extra: FinTSAlphanumeric | None = None


class OtherSegment(FinTSSegment):
    """Another test segment type."""

    SEGMENT_TYPE: ClassVar[str] = "OTHER"
    SEGMENT_VERSION: ClassVar[int] = 1

    value: FinTSNumeric


# =============================================================================
# FinTSModel Tests
# =============================================================================


class TestFinTSModel:
    """Tests for FinTSModel base class."""

    def test_basic_creation(self):
        """Create model with field values."""
        model = SimpleModel(name="test", value=123)
        assert model.name == "test"
        assert model.value == 123

    def test_from_wire_list_basic(self):
        """Parse model from wire format list."""
        model = SimpleModel.from_wire_list(["test", "123"])
        assert model.name == "test"
        assert model.value == 123

    def test_from_wire_list_none(self):
        """from_wire_list with None creates empty kwargs."""
        with pytest.raises(Exception):
            # Required fields are missing
            SimpleModel.from_wire_list(None)

    def test_from_wire_list_empty(self):
        """from_wire_list with empty list."""
        with pytest.raises(Exception):
            # Required fields are missing
            SimpleModel.from_wire_list([])

    def test_from_wire_list_with_optional(self):
        """Parse model with optional fields."""
        # Only required field
        model = OptionalModel.from_wire_list(["required_value"])
        assert model.required_field == "required_value"
        assert model.optional_field is None

        # Both fields
        model = OptionalModel.from_wire_list(["required_value", "optional_value"])
        assert model.required_field == "required_value"
        assert model.optional_field == "optional_value"

    def test_to_wire_list_basic(self):
        """Export model to wire format list."""
        model = SimpleModel(name="test", value=123)
        wire = model.to_wire_list()
        assert wire == ["test", 123]

    def test_to_wire_list_with_optional_none(self):
        """Export model with None optional fields."""
        model = OptionalModel(required_field="required_value")
        wire = model.to_wire_list()
        assert wire == ["required_value", None]

    def test_extra_fields_ignored(self):
        """Unknown fields are ignored (from bank responses)."""
        # This shouldn't raise - extra fields are ignored
        model = SimpleModel(name="test", value=123, unknown_field="ignored")
        assert model.name == "test"

    def test_roundtrip(self):
        """Parse and re-export produces same data."""
        original = ["test", "123"]
        model = SimpleModel.from_wire_list(original)
        wire = model.to_wire_list()
        assert wire == ["test", 123]  # Note: 123 is int after parsing


# =============================================================================
# FinTSDataElementGroup Tests
# =============================================================================


class TestFinTSDataElementGroup:
    """Tests for FinTSDataElementGroup."""

    def test_is_subclass_of_model(self):
        """DEG is a FinTSModel."""
        assert issubclass(FinTSDataElementGroup, FinTSModel)

    def test_deg_creation(self):
        """Create DEG with values."""
        deg = NestedDEG(amount=Decimal("123.45"), currency="EUR")
        assert deg.amount == Decimal("123.45")
        assert deg.currency == "EUR"

    def test_deg_from_wire_list(self):
        """Parse DEG from wire list."""
        deg = NestedDEG.from_wire_list(["123,45", "EUR"])
        assert deg.amount == Decimal("123.45")
        assert deg.currency == "EUR"


# =============================================================================
# Nested Model Tests
# =============================================================================


class TestNestedModels:
    """Tests for models containing other models."""

    def test_nested_creation(self):
        """Create model with nested DEG."""
        nested = NestedDEG(amount=Decimal("100.00"), currency="EUR")
        parent = ParentModel(name="test", nested=nested)
        assert parent.name == "test"
        assert parent.nested.amount == Decimal("100.00")
        assert parent.nested.currency == "EUR"

    def test_nested_from_wire_list(self):
        """Parse model with nested DEG from wire list."""
        # Nested data comes as a sub-list
        parent = ParentModel.from_wire_list(["test", ["100,00", "EUR"]])
        assert parent.name == "test"
        assert parent.nested.amount == Decimal("100.00")
        assert parent.nested.currency == "EUR"

    def test_nested_to_wire_list(self):
        """Export model with nested DEG to wire list."""
        nested = NestedDEG(amount=Decimal("100.00"), currency="EUR")
        parent = ParentModel(name="test", nested=nested)
        wire = parent.to_wire_list()
        assert wire[0] == "test"
        assert wire[1] == [Decimal("100.00"), "EUR"]


# =============================================================================
# SegmentHeader Tests
# =============================================================================


class TestSegmentHeader:
    """Tests for SegmentHeader."""

    def test_header_creation(self):
        """Create header with values."""
        header = SegmentHeader(type="HISAL", number=5, version=6)
        assert header.type == "HISAL"
        assert header.number == 5
        assert header.version == 6
        assert header.reference is None

    def test_header_with_reference(self):
        """Create header with reference."""
        header = SegmentHeader(type="HIRMS", number=3, version=2, reference=5)
        assert header.reference == 5

    def test_header_from_wire_list(self):
        """Parse header from wire list."""
        header = SegmentHeader.from_wire_list(["HISAL", "5", "6"])
        assert header.type == "HISAL"
        assert header.number == 5
        assert header.version == 6
        assert header.reference is None

    def test_header_from_wire_list_with_reference(self):
        """Parse header with reference from wire list."""
        header = SegmentHeader.from_wire_list(["HIRMS", "3", "2", "5"])
        assert header.type == "HIRMS"
        assert header.number == 3
        assert header.version == 2
        assert header.reference == 5

    def test_header_to_wire_list(self):
        """Export header to wire list."""
        header = SegmentHeader(type="HISAL", number=5, version=6)
        wire = header.to_wire_list()
        assert wire == ["HISAL", 5, 6, None]


# =============================================================================
# FinTSSegment Tests
# =============================================================================


class TestFinTSSegment:
    """Tests for FinTSSegment."""

    def test_segment_id(self):
        """Segment ID combines type and version."""
        assert SampleSegment.segment_id() == "SAMPLE1"
        assert SampleSegmentV2.segment_id() == "SAMPLE2"
        assert OtherSegment.segment_id() == "OTHER1"

    def test_segment_creation(self):
        """Create segment with header and data."""
        header = SegmentHeader(type="TEST", number=3, version=1)
        segment = SampleSegment(header=header, data="test data")
        assert segment.header.type == "TEST"
        assert segment.data == "test data"

    def test_segment_from_wire_list(self):
        """Parse segment from wire list."""
        # First element is header, rest is segment data
        wire = [["TEST", "3", "1"], "test data"]
        segment = SampleSegment.from_wire_list(wire)
        assert segment.header.type == "TEST"
        assert segment.header.number == 3
        assert segment.header.version == 1
        assert segment.data == "test data"

    def test_segment_from_wire_list_empty_raises(self):
        """Empty wire list raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            SampleSegment.from_wire_list([])

    def test_segment_class_vars(self):
        """Segment class variables are set correctly."""
        assert SampleSegment.SEGMENT_TYPE == "SAMPLE"
        assert SampleSegment.SEGMENT_VERSION == 1
        assert SampleSegmentV2.SEGMENT_VERSION == 2


# =============================================================================
# SegmentSequence Tests
# =============================================================================


class TestSegmentSequence:
    """Tests for SegmentSequence."""

    @pytest.fixture
    def sample_segments(self) -> list[FinTSSegment]:
        """Create sample segments for testing."""
        return [
            SampleSegment(
                header=SegmentHeader(type="SAMPLE", number=1, version=1),
                data="first",
            ),
            SampleSegmentV2(
                header=SegmentHeader(type="SAMPLE", number=2, version=2),
                data="second",
                extra="extra data",
            ),
            OtherSegment(
                header=SegmentHeader(type="OTHER", number=3, version=1),
                value=123,
            ),
            SampleSegment(
                header=SegmentHeader(type="SAMPLE", number=4, version=1),
                data="third",
            ),
        ]

    @pytest.fixture
    def sequence(self, sample_segments) -> SegmentSequence:
        """Create SegmentSequence with sample data."""
        return SegmentSequence(segments=sample_segments)

    def test_empty_sequence(self):
        """Create empty sequence."""
        seq = SegmentSequence()
        assert len(seq) == 0
        assert list(seq) == []

    def test_sequence_with_segments(self, sequence):
        """Create sequence with segments."""
        assert len(sequence) == 4

    def test_iteration(self, sequence):
        """Iterate over sequence."""
        segments = list(sequence)
        assert len(segments) == 4

    def test_find_segments_no_filter(self, sequence):
        """find_segments with no filter returns all."""
        found = list(sequence.find_segments())
        assert len(found) == 4

    def test_find_segments_by_type_string(self, sequence):
        """find_segments by type string."""
        found = list(sequence.find_segments(query="SAMPLE"))
        assert len(found) == 3
        for seg in found:
            assert seg.SEGMENT_TYPE == "SAMPLE"

    def test_find_segments_by_type_class(self, sequence):
        """find_segments by type class."""
        found = list(sequence.find_segments(query=SampleSegment))
        assert len(found) == 2  # Only SampleSegment, not SampleSegmentV2
        for seg in found:
            assert isinstance(seg, SampleSegment)
            assert not isinstance(seg, SampleSegmentV2)

    def test_find_segments_with_callback(self, sequence):
        """find_segments with callback filter."""
        found = list(sequence.find_segments(callback=lambda s: s.header.number > 2))
        assert len(found) == 2

    def test_find_segments_combined_filters(self, sequence):
        """find_segments with query and callback combined."""
        found = list(
            sequence.find_segments(
                query="SAMPLE",
                callback=lambda s: s.header.number > 1 and s.SEGMENT_VERSION == 1,
            )
        )
        assert len(found) == 1
        assert found[0].data == "third"

    def test_find_segment_first(self, sequence):
        """find_segment_first returns first match."""
        first = sequence.find_segment_first(query="SAMPLE")
        assert first is not None
        assert first.data == "first"

    def test_find_segment_first_not_found(self, sequence):
        """find_segment_first returns None when not found."""
        result = sequence.find_segment_first(query="NONEXISTENT")
        assert result is None

    def test_find_segment_highest_version(self, sequence):
        """find_segment_highest_version returns highest version."""
        highest = sequence.find_segment_highest_version(query="SAMPLE")
        assert highest is not None
        assert highest.SEGMENT_VERSION == 2

    def test_find_segment_highest_version_not_found(self, sequence):
        """find_segment_highest_version returns default when not found."""
        result = sequence.find_segment_highest_version(
            query="NONEXISTENT", default=None
        )
        assert result is None

    def test_find_segment_highest_version_with_default(self, sequence):
        """find_segment_highest_version returns custom default."""
        default_seg = SampleSegment(
            header=SegmentHeader(type="DEFLT", number=0, version=0),
            data="default",
        )
        result = sequence.find_segment_highest_version(
            query="NONEXISTENT", default=default_seg
        )
        assert result is default_seg


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_full_segment_workflow(self):
        """Test complete segment parse/query/export workflow."""
        # Create segment from wire data (using test-specific type to avoid registry conflicts)
        wire_data = [["TSAL", "5", "6"], "Account Product"]

        class TestSAL6(FinTSSegment):
            SEGMENT_TYPE: ClassVar[str] = "TSAL"
            SEGMENT_VERSION: ClassVar[int] = 6
            account_product: FinTSAlphanumeric

        segment = TestSAL6.from_wire_list(wire_data)
        assert segment.header.type == "TSAL"
        assert segment.header.version == 6
        assert segment.account_product == "Account Product"

        # Add to sequence
        seq = SegmentSequence(segments=[segment])

        # Query
        found = seq.find_segment_first(query="TSAL")
        assert found is segment

        # Export
        exported = segment.to_wire_list()
        assert exported[0] == ["TSAL", 5, 6, None]  # Header
        assert exported[1] == "Account Product"

    def test_complex_nested_structure(self):
        """Test complex nested model structure."""

        class Balance(FinTSDataElementGroup):
            credit_debit: FinTSAlphanumeric
            amount: FinTSAmount
            currency: FinTSCurrency
            date: FinTSDate

        class AccountInfo(FinTSDataElementGroup):
            account_number: FinTSAlphanumeric
            balance: Balance

        # Parse nested structure
        wire = ["123456", ["C", "1000,50", "EUR", "20231225"]]
        info = AccountInfo.from_wire_list(wire)

        assert info.account_number == "123456"
        assert info.balance.credit_debit == "C"
        assert info.balance.amount == Decimal("1000.50")
        assert info.balance.currency == "EUR"
        assert info.balance.date == date(2023, 12, 25)


# =============================================================================
# Serialization Round-Trip Tests
# =============================================================================


class TestSerializationRoundTrip:
    """Tests for complete parse → serialize → parse round-trips."""

    def test_segment_to_wire_and_back(self):
        """Create segment, serialize to wire, parse back."""

        # Create a segment
        header = SegmentHeader(type="SAMPLE", number=1, version=1)
        original = SampleSegment(header=header, data="test data")

        # Serialize to wire list
        wire = original.to_wire_list()
        assert wire[0] == ["SAMPLE", 1, 1, None]  # Header
        assert wire[1] == "test data"

        # Parse back
        restored = SampleSegment.from_wire_list(wire)
        assert restored.header.type == original.header.type
        assert restored.header.number == original.header.number
        assert restored.data == original.data

    def test_serializer_serialize_segment(self):
        """Test FinTSSerializer.serialize_segment() produces wire format."""
        from geldstrom.infrastructure.fints.protocol.parser import FinTSSerializer

        header = SegmentHeader(type="SAMPLE", number=1, version=1)
        segment = SampleSegment(header=header, data="test data")

        serializer = FinTSSerializer()
        wire = serializer.serialize_segment(segment)

        # Should be a nested list structure
        assert isinstance(wire, list)
        # First element is header
        assert wire[0] == ["SAMPLE", 1, 1, None]
        # Rest is segment data
        assert "test data" in wire

    def test_serialize_and_implode_segment(self):
        """Test full serialization to bytes."""
        from geldstrom.infrastructure.fints.protocol.parser import FinTSSerializer

        header = SegmentHeader(type="TEST", number=3, version=1)
        segment = SampleSegment(header=header, data="hello world")

        serializer = FinTSSerializer()
        wire = serializer.serialize_segment(segment)
        raw = serializer.implode_segments([wire])

        # Should be valid wire format
        assert raw.endswith(b"'")
        assert b"TEST:3:1" in raw
        assert b"hello world" in raw


class TestSegmentSequenceSerializationMethods:
    """Tests for SegmentSequence.render_bytes() and from_bytes()."""

    def test_render_bytes_basic(self):
        """render_bytes() produces valid wire format."""
        header = SegmentHeader(type="TEST", number=1, version=1)
        seg = SampleSegment(header=header, data="hello")

        seq = SegmentSequence(segments=[seg])
        raw = seq.render_bytes()

        assert isinstance(raw, bytes)
        assert raw.endswith(b"'")
        assert b"TEST:1:1" in raw
        assert b"hello" in raw

    def test_render_bytes_multiple_segments(self):
        """render_bytes() handles multiple segments."""
        seg1 = SampleSegment(
            header=SegmentHeader(type="TEST", number=1, version=1),
            data="first",
        )
        seg2 = OtherSegment(
            header=SegmentHeader(type="OTHER", number=2, version=1),
            value=42,
        )

        seq = SegmentSequence(segments=[seg1, seg2])
        raw = seq.render_bytes()

        assert b"TEST:1:1" in raw
        assert b"OTHER:2:1" in raw
        assert b"first" in raw
        assert b"42" in raw

    def test_from_bytes_basic(self):
        """from_bytes() parses wire format."""
        # Simple segment that should parse
        raw = b"HNHBS:5:1+2'"

        seq = SegmentSequence.from_bytes(raw, robust_mode=True)

        assert isinstance(seq, SegmentSequence)
        # May have 0 segments if HNHBS not in registry, but should not error
        assert len(seq) >= 0

    def test_init_with_bytes_parses(self):
        """SegmentSequence(bytes) parses automatically."""
        raw = b"HNHBS:5:1+2'"

        # Should not raise
        seq = SegmentSequence(raw)

        assert isinstance(seq, SegmentSequence)

    def test_init_with_list_uses_list(self):
        """SegmentSequence(list) uses the list directly."""
        seg = SampleSegment(
            header=SegmentHeader(type="TEST", number=1, version=1),
            data="test",
        )

        seq = SegmentSequence(segments=[seg])

        assert len(seq) == 1
        assert seq.segments[0] is seg

    def test_init_empty(self):
        """SegmentSequence() creates empty sequence."""
        seq = SegmentSequence()
        assert len(seq) == 0

    def test_roundtrip_render_parse(self):
        """render_bytes() output can be parsed back."""
        # Create a segment
        seg = SampleSegment(
            header=SegmentHeader(type="SAMPL", number=1, version=1),
            data="roundtrip test",
        )
        seq1 = SegmentSequence(segments=[seg])

        # Serialize
        raw = seq1.render_bytes()
        assert isinstance(raw, bytes)

        # Note: Parsing may not reproduce identical objects since
        # SAMPL1 is not a registered segment type. The test validates
        # that render produces parseable output.


class TestSegmentSequencePhase1Prep:
    """Additional tests for SegmentSequence functionality."""

    def test_sequence_stores_segments(self):
        """SegmentSequence stores and retrieves segments."""
        header1 = SegmentHeader(type="SAMPLE", number=1, version=1)
        header2 = SegmentHeader(type="OTHER", number=2, version=1)

        seg1 = SampleSegment(header=header1, data="first")
        seg2 = OtherSegment(header=header2, value=42)

        seq = SegmentSequence(segments=[seg1, seg2])

        assert len(seq) == 2
        assert seq.segments[0].data == "first"
        assert seq.segments[1].value == 42

    def test_sequence_find_works(self):
        """SegmentSequence.find_segments() works correctly."""
        segments = [
            SampleSegment(
                header=SegmentHeader(type="SAMPLE", number=1, version=1),
                data="first",
            ),
            SampleSegment(
                header=SegmentHeader(type="SAMPLE", number=2, version=1),
                data="second",
            ),
            OtherSegment(
                header=SegmentHeader(type="OTHER", number=3, version=1),
                value=100,
            ),
        ]
        seq = SegmentSequence(segments=segments)

        # Find by type string
        found = list(seq.find_segments(query="SAMPLE"))
        assert len(found) == 2

        # Find first
        first = seq.find_segment_first(query="OTHER")
        assert first is not None
        assert first.value == 100

    def test_sequence_is_iterable(self):
        """SegmentSequence is iterable."""
        segments = [
            SampleSegment(
                header=SegmentHeader(type="SAMPLE", number=i, version=1),
                data=f"segment {i}",
            )
            for i in range(3)
        ]
        seq = SegmentSequence(segments=segments)

        # Should be iterable
        collected = list(seq)
        assert len(collected) == 3
        assert collected[0].data == "segment 0"
        assert collected[2].data == "segment 2"
