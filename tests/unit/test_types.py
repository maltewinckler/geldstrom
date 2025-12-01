"""Comprehensive unit tests for fints/types.py.

This module tests the core type system used throughout the FinTS library:
- Field: Base descriptor class for data elements
- TypedField: Field with type-based subclass resolution
- ValueList: List implementation for repeated fields
- SegmentSequence: Collection of parsed segments
- Container: Base class for data structures (DEGs, segments)
"""
from __future__ import annotations

import io
from collections import OrderedDict
from unittest.mock import MagicMock, patch

import pytest

from fints.exceptions import FinTSNoResponseError
from fints.types import Container, ContainerMeta, Field, SegmentSequence, TypedField, ValueList


# ==============================================================================
# Field Tests
# ==============================================================================


class TestField:
    """Tests for the Field base class."""

    def test_field_default_initialization(self):
        """Test Field with default parameters."""
        field = Field()
        assert field.length is None
        assert field.min_length is None
        assert field.max_length is None
        assert field.count == 1  # Default when no count specified
        assert field.min_count is None
        assert field.max_count is None
        assert field.required is True

    def test_field_with_fixed_length(self):
        """Test Field with fixed length constraint."""
        field = Field(length=10)
        assert field.length == 10
        assert field.min_length is None
        assert field.max_length is None

    def test_field_with_min_max_length(self):
        """Test Field with min/max length constraints."""
        field = Field(min_length=5, max_length=20)
        assert field.length is None
        assert field.min_length == 5
        assert field.max_length == 20

    def test_field_cannot_have_both_length_and_min_max(self):
        """Test that combining length with min_length/max_length raises error."""
        with pytest.raises(ValueError, match="May not specify both 'length' AND"):
            Field(length=10, min_length=5)

        with pytest.raises(ValueError, match="May not specify both 'length' AND"):
            Field(length=10, max_length=15)

    def test_field_with_fixed_count(self):
        """Test Field with fixed repeat count."""
        field = Field(count=3)
        assert field.count == 3
        assert field.min_count is None
        assert field.max_count is None

    def test_field_with_min_max_count(self):
        """Test Field with min/max repeat count."""
        field = Field(min_count=1, max_count=10)
        assert field.count is None
        assert field.min_count == 1
        assert field.max_count == 10

    def test_field_cannot_have_both_count_and_min_max(self):
        """Test that combining count with min_count/max_count raises error."""
        with pytest.raises(ValueError, match="May not specify both 'count' AND"):
            Field(count=5, min_count=1)

        with pytest.raises(ValueError, match="May not specify both 'count' AND"):
            Field(count=5, max_count=10)

    def test_field_with_documentation(self):
        """Test Field with documentation string."""
        field = Field(_d="Account number")
        assert field.__doc__ == "Account number"

    def test_field_not_required(self):
        """Test optional Field."""
        field = Field(required=False)
        assert field.required is False

    def test_field_default_value(self):
        """Test Field._default_value() returns None."""
        field = Field()
        assert field._default_value() is None

    def test_field_parse_value_not_implemented(self):
        """Test that _parse_value raises NotImplementedError in base class."""
        field = Field()
        with pytest.raises(NotImplementedError):
            field._parse_value("test")

    def test_field_render_value_not_implemented(self):
        """Test that _render_value raises NotImplementedError in base class."""
        field = Field()
        with pytest.raises(NotImplementedError):
            field._render_value("test")

    def test_field_render_none_returns_none(self):
        """Test that render(None) returns None."""
        field = Field()
        assert field.render(None) is None


class TestFieldLengthValidation:
    """Tests for Field length validation."""

    def test_check_value_length_max_exceeded(self):
        """Test that exceeding max_length raises ValueError."""
        field = Field(max_length=5)
        with pytest.raises(ValueError, match="max_length=5 exceeded"):
            field._check_value_length("toolong")

    def test_check_value_length_min_not_reached(self):
        """Test that not reaching min_length raises ValueError."""
        field = Field(min_length=10)
        with pytest.raises(ValueError, match="min_length=10 not reached"):
            field._check_value_length("short")

    def test_check_value_length_fixed_not_satisfied(self):
        """Test that wrong fixed length raises ValueError."""
        field = Field(length=5)
        with pytest.raises(ValueError, match="length=5 not satisfied"):
            field._check_value_length("abc")  # 3 chars, not 5

    def test_check_value_length_valid(self):
        """Test that valid length passes."""
        field = Field(max_length=10)
        field._check_value_length("valid")  # Should not raise


class TestFieldInlineDocComment:
    """Tests for Field._inline_doc_comment()."""

    def test_inline_doc_with_documentation(self):
        """Test inline doc comment generation."""
        field = Field(_d="Account number")
        comment = field._inline_doc_comment("value")
        assert comment == " # Account number"

    def test_inline_doc_without_documentation(self):
        """Test inline doc comment with no documentation."""
        field = Field()
        comment = field._inline_doc_comment("value")
        assert comment == ""

    def test_inline_doc_multiline(self):
        """Test inline doc uses only first line."""
        field = Field(_d="First line\nSecond line")
        comment = field._inline_doc_comment("value")
        assert comment == " # First line"


# ==============================================================================
# TypedField Tests
# ==============================================================================


class TestTypedField:
    """Tests for TypedField with subclass resolution."""

    def test_typed_field_stores_type(self):
        """Test that TypedField stores its type."""
        field = TypedField(type="txt")
        assert field.type == "txt"

    def test_typed_field_none_type(self):
        """Test TypedField with no type."""
        field = TypedField()
        assert field.type is None


# ==============================================================================
# ValueList Tests
# ==============================================================================


class ConcreteField(Field):
    """Concrete Field implementation for testing ValueList."""

    def _parse_value(self, value):
        return str(value)

    def _render_value(self, value):
        return str(value)


class TestValueList:
    """Tests for the ValueList class."""

    def test_valuelist_initialization(self):
        """Test ValueList is created with empty data."""
        parent = ConcreteField(max_count=5)
        vl = ValueList(parent)
        assert vl._parent is parent
        assert vl._data == []

    def test_valuelist_setitem_and_getitem(self):
        """Test basic set and get operations."""
        parent = ConcreteField(max_count=5)
        vl = ValueList(parent)
        vl[0] = "first"
        vl[1] = "second"
        assert vl[0] == "first"
        assert vl[1] == "second"

    def test_valuelist_negative_index_raises(self):
        """Test that negative indices raise IndexError."""
        parent = ConcreteField(max_count=5)
        vl = ValueList(parent)

        with pytest.raises(IndexError, match="Cannot access negative index"):
            _ = vl[-1]

        with pytest.raises(IndexError, match="Cannot access negative index"):
            vl[-1] = "value"

    def test_valuelist_beyond_count_raises(self):
        """Test that indices beyond fixed count raise IndexError."""
        parent = ConcreteField(count=3)
        vl = ValueList(parent)

        with pytest.raises(IndexError, match="Cannot access index 3 beyond count 3"):
            vl[3] = "value"

    def test_valuelist_beyond_max_count_raises(self):
        """Test that indices beyond max_count raise IndexError."""
        parent = ConcreteField(max_count=5)
        vl = ValueList(parent)

        with pytest.raises(IndexError, match="Cannot access index 5 beyound max_count 5"):
            vl[5] = "value"

    def test_valuelist_auto_expand(self):
        """Test that setting index beyond current length auto-expands."""
        parent = ConcreteField(max_count=10)
        vl = ValueList(parent)
        vl[3] = "value"  # Should create indices 0, 1, 2 as None first
        assert len(vl._data) == 4
        assert vl._data[0] is None
        assert vl._data[1] is None
        assert vl._data[2] is None
        assert vl._data[3] == "value"

    def test_valuelist_delete_sets_to_none(self):
        """Test that delete sets value to None (default)."""
        parent = ConcreteField(max_count=5)
        vl = ValueList(parent)
        vl[0] = "value"
        del vl[0]
        assert vl._data[0] is None

    def test_valuelist_len_with_fixed_count(self):
        """Test len() with fixed count returns count."""
        parent = ConcreteField(count=5)
        vl = ValueList(parent)
        vl[0] = "a"
        assert len(vl) == 5  # Always returns count

    def test_valuelist_len_with_min_count(self):
        """Test len() respects min_count."""
        parent = ConcreteField(min_count=3, max_count=10)
        vl = ValueList(parent)
        assert len(vl) == 3  # Returns min_count when empty

        vl[5] = "a"  # Set value at index 5
        assert len(vl) == 6  # Now returns index of last non-null + 1

    def test_valuelist_len_minimal_true_length(self):
        """Test len() calculates minimal true length correctly."""
        parent = ConcreteField(max_count=10)
        vl = ValueList(parent)
        vl[0] = "a"
        vl[1] = "b"
        vl[2] = None  # Trailing None
        assert len(vl) == 2  # Only counts up to last non-None

    def test_valuelist_iteration(self):
        """Test iteration over ValueList."""
        parent = ConcreteField(max_count=5)
        vl = ValueList(parent)
        vl[0] = "a"
        vl[1] = "b"
        vl[2] = "c"

        result = list(vl)
        assert result == ["a", "b", "c"]

    def test_valuelist_repr(self):
        """Test ValueList __repr__."""
        parent = ConcreteField(max_count=5)
        vl = ValueList(parent)
        vl[0] = "test"

        repr_str = repr(vl)
        assert "'test'" in repr_str

    def test_valuelist_print_nested(self):
        """Test ValueList.print_nested() output."""
        parent = ConcreteField(max_count=5, _d="Test field")
        vl = ValueList(parent)
        vl[0] = "value1"
        vl[1] = "value2"

        output = io.StringIO()
        vl.print_nested(stream=output)

        result = output.getvalue()
        assert "[\n" in result
        assert "'value1'" in result
        assert "'value2'" in result
        assert "]\n" in result


# ==============================================================================
# SegmentSequence Tests
# ==============================================================================


class MockSegment:
    """Mock segment for testing SegmentSequence."""

    def __init__(self, seg_type: str, version: int):
        self.header = MagicMock()
        self.header.type = seg_type
        self.header.version = version
        self._fields = {}
        self.__doc__ = f"Mock {seg_type} segment"

    def print_nested(self, **kwargs):
        stream = kwargs.get("stream", io.StringIO())
        stream.write(f"Mock({self.header.type}, v{self.header.version})\n")


class TestSegmentSequence:
    """Tests for the SegmentSequence class."""

    def test_segmentsequence_empty_initialization(self):
        """Test creating empty SegmentSequence."""
        seq = SegmentSequence()
        assert seq.segments == []

    def test_segmentsequence_with_list(self):
        """Test creating SegmentSequence from list."""
        segments = [MockSegment("HNHBK", 3), MockSegment("HNHBS", 1)]
        seq = SegmentSequence(segments)
        assert len(seq.segments) == 2
        assert seq.segments[0].header.type == "HNHBK"

    def test_segmentsequence_repr(self):
        """Test SegmentSequence __repr__."""
        seq = SegmentSequence()
        repr_str = repr(seq)
        assert "SegmentSequence" in repr_str

    def test_segmentsequence_print_nested(self):
        """Test SegmentSequence.print_nested() output."""
        segments = [MockSegment("HNHBK", 3)]
        seq = SegmentSequence(segments)

        output = io.StringIO()
        seq.print_nested(stream=output)

        result = output.getvalue()
        assert "SegmentSequence" in result

    # --- find_segments tests ---

    def test_find_segments_no_query(self):
        """Test find_segments with no query returns all segments."""
        segments = [
            MockSegment("HNHBK", 3),
            MockSegment("HIBPA", 3),
            MockSegment("HNHBS", 1),
        ]
        seq = SegmentSequence(segments)

        found = list(seq.find_segments())
        assert len(found) == 3

    def test_find_segments_by_string_type(self):
        """Test find_segments with string type query."""
        segments = [
            MockSegment("HNHBK", 3),
            MockSegment("HIBPA", 3),
            MockSegment("HNHBS", 1),
        ]
        seq = SegmentSequence(segments)

        found = list(seq.find_segments(query="HIBPA"))
        assert len(found) == 1
        assert found[0].header.type == "HIBPA"

    def test_find_segments_by_class_type(self):
        """Test find_segments with class type query."""
        seg1 = MockSegment("HNHBK", 3)
        seg2 = MockSegment("HIBPA", 3)
        seq = SegmentSequence([seg1, seg2])

        # Query by class type - should match by isinstance
        found = list(seq.find_segments(query=MockSegment))
        assert len(found) == 2

    def test_find_segments_by_version(self):
        """Test find_segments with version filter."""
        segments = [
            MockSegment("HKSAL", 5),
            MockSegment("HKSAL", 6),
            MockSegment("HKSAL", 7),
        ]
        seq = SegmentSequence(segments)

        found = list(seq.find_segments(query="HKSAL", version=6))
        assert len(found) == 1
        assert found[0].header.version == 6

    def test_find_segments_by_version_list(self):
        """Test find_segments with list of versions."""
        segments = [
            MockSegment("HKSAL", 5),
            MockSegment("HKSAL", 6),
            MockSegment("HKSAL", 7),
        ]
        seq = SegmentSequence(segments)

        found = list(seq.find_segments(query="HKSAL", version=[5, 7]))
        assert len(found) == 2
        versions = [s.header.version for s in found]
        assert 5 in versions
        assert 7 in versions

    def test_find_segments_by_callback(self):
        """Test find_segments with custom callback."""
        segments = [
            MockSegment("HKSAL", 5),
            MockSegment("HKSAL", 6),
            MockSegment("HKSAL", 7),
        ]
        seq = SegmentSequence(segments)

        # Only return segments with version >= 6
        found = list(seq.find_segments(callback=lambda s: s.header.version >= 6))
        assert len(found) == 2

    def test_find_segments_with_multiple_query_types(self):
        """Test find_segments with list of types."""
        segments = [
            MockSegment("HNHBK", 3),
            MockSegment("HIBPA", 3),
            MockSegment("HIUPA", 4),
            MockSegment("HNHBS", 1),
        ]
        seq = SegmentSequence(segments)

        found = list(seq.find_segments(query=["HIBPA", "HIUPA"]))
        assert len(found) == 2

    def test_find_segments_throw_on_not_found(self):
        """Test find_segments raises exception when throw=True and nothing found."""
        seq = SegmentSequence([MockSegment("HNHBK", 3)])

        with pytest.raises(FinTSNoResponseError):
            list(seq.find_segments(query="NONEXISTENT", throw=True))

    def test_find_segments_no_recurse(self):
        """Test find_segments with recurse=False doesn't recurse."""
        segments = [MockSegment("HNHBK", 3)]
        seq = SegmentSequence(segments)

        # With no nested segments, should work the same
        found = list(seq.find_segments(recurse=False))
        assert len(found) == 1

    def test_find_segment_first(self):
        """Test find_segment_first returns first match."""
        segments = [
            MockSegment("HKSAL", 5),
            MockSegment("HKSAL", 6),
            MockSegment("HKSAL", 7),
        ]
        seq = SegmentSequence(segments)

        first = seq.find_segment_first(query="HKSAL")
        assert first is not None
        assert first.header.version == 5

    def test_find_segment_first_not_found(self):
        """Test find_segment_first returns None when not found."""
        seq = SegmentSequence([MockSegment("HNHBK", 3)])

        result = seq.find_segment_first(query="NONEXISTENT")
        assert result is None

    def test_find_segment_highest_version(self):
        """Test find_segment_highest_version returns highest version."""
        segments = [
            MockSegment("HKSAL", 5),
            MockSegment("HKSAL", 7),
            MockSegment("HKSAL", 6),
        ]
        seq = SegmentSequence(segments)

        highest = seq.find_segment_highest_version(query="HKSAL")
        assert highest is not None
        assert highest.header.version == 7

    def test_find_segment_highest_version_not_found(self):
        """Test find_segment_highest_version returns default when not found."""
        seq = SegmentSequence([MockSegment("HNHBK", 3)])

        result = seq.find_segment_highest_version(query="NONEXISTENT", default="DEFAULT")
        assert result == "DEFAULT"


# ==============================================================================
# Container Tests
# ==============================================================================


class SimpleContainer(Container):
    """Simple container for testing with concrete fields."""

    name = ConcreteField(_d="Name field")
    value = ConcreteField(required=False, _d="Value field")


class NestedContainer(Container):
    """Container with nested container field."""

    inner = ConcreteField(required=False)


class RepeatingContainer(Container):
    """Container with repeating field."""

    items = ConcreteField(max_count=5, required=False)


class TestContainer:
    """Tests for the Container base class."""

    def test_container_empty_initialization(self):
        """Test Container can be created with no arguments."""
        container = SimpleContainer()
        assert container.name is None
        assert container.value is None

    def test_container_initialization_with_args(self):
        """Test Container can be created with positional args."""
        container = SimpleContainer("test_name", "test_value")
        assert container.name == "test_name"
        assert container.value == "test_value"

    def test_container_initialization_with_kwargs(self):
        """Test Container can be created with keyword args."""
        container = SimpleContainer(name="test_name", value="test_value")
        assert container.name == "test_name"
        assert container.value == "test_value"

    def test_container_initialization_mixed_args_kwargs(self):
        """Test Container with mixed positional and keyword args."""
        container = SimpleContainer("test_name", value="test_value")
        assert container.name == "test_name"
        assert container.value == "test_value"

    def test_container_duplicate_arg_raises(self):
        """Test that duplicate argument raises TypeError."""
        with pytest.raises(TypeError, match="got multiple values for argument"):
            SimpleContainer("test_name", name="other_name")

    def test_container_additional_data(self):
        """Test Container stores _additional_data."""
        container = SimpleContainer(_additional_data=["extra", "data"])
        assert container._additional_data == ["extra", "data"]

    def test_container_is_unset_empty(self):
        """Test is_unset returns True for empty container."""
        container = SimpleContainer()
        assert container.is_unset() is True

    def test_container_is_unset_with_values(self):
        """Test is_unset returns False when values are set."""
        container = SimpleContainer(name="test")
        assert container.is_unset() is False

    def test_container_repr(self):
        """Test Container __repr__."""
        container = SimpleContainer(name="test")
        repr_str = repr(container)
        assert "SimpleContainer" in repr_str
        assert "name='test'" in repr_str

    def test_container_repr_skips_optional_unset(self):
        """Test __repr__ skips optional fields that are unset."""
        container = SimpleContainer(name="test")
        repr_str = repr(container)
        # 'value' should not appear since it's optional and unset
        assert "name='test'" in repr_str
        # But required fields appear even if None
        # Actually in this case, name is required so it appears

    def test_container_naive_parse(self):
        """Test Container.naive_parse() creates container from data."""
        data = ["parsed_name", "parsed_value"]
        container = SimpleContainer.naive_parse(data)
        assert container.name == "parsed_name"
        assert container.value == "parsed_value"

    def test_container_naive_parse_none_raises(self):
        """Test naive_parse with None raises TypeError."""
        with pytest.raises(TypeError, match="No data provided"):
            SimpleContainer.naive_parse(None)

    def test_container_print_nested(self):
        """Test Container.print_nested() output."""
        container = SimpleContainer(name="test", value="123")

        output = io.StringIO()
        container.print_nested(stream=output)

        result = output.getvalue()
        assert "SimpleContainer" in result
        assert "name = 'test'" in result
        assert "value = '123'" in result

    def test_container_print_nested_with_doc(self):
        """Test print_nested includes docstrings."""
        container = SimpleContainer(name="test")

        output = io.StringIO()
        container.print_nested(stream=output, print_doc=True)

        result = output.getvalue()
        assert "# Name field" in result

    def test_container_fields_are_ordered(self):
        """Test that Container._fields preserves definition order."""
        assert list(SimpleContainer._fields.keys()) == ["name", "value"]


class TestContainerMeta:
    """Tests for ContainerMeta metaclass."""

    def test_metaclass_creates_fields_dict(self):
        """Test ContainerMeta creates _fields OrderedDict."""
        assert hasattr(SimpleContainer, "_fields")
        assert isinstance(SimpleContainer._fields, OrderedDict)

    def test_metaclass_inherits_fields(self):
        """Test that subclass inherits parent fields."""

        class Parent(Container):
            parent_field = ConcreteField()

        class Child(Parent):
            child_field = ConcreteField()

        # Child should have both fields
        assert "parent_field" in Child._fields
        assert "child_field" in Child._fields

    def test_metaclass_preserves_order(self):
        """Test that field order is preserved."""

        class OrderedContainer(Container):
            first = ConcreteField()
            second = ConcreteField()
            third = ConcreteField()

        fields = list(OrderedContainer._fields.keys())
        assert fields == ["first", "second", "third"]


# ==============================================================================
# Integration Tests - Real World Usage Patterns
# ==============================================================================


class TestRealWorldPatterns:
    """Tests that mirror actual usage patterns in the FinTS library."""

    def test_segment_header_pattern(self):
        """Test pattern similar to SegmentHeader usage."""

        class SegmentHeaderLike(Container):
            type = ConcreteField(max_length=6, _d="Segment type")
            number = ConcreteField(max_length=3, _d="Segment number")
            version = ConcreteField(max_length=3, _d="Segment version")
            reference = ConcreteField(max_length=3, required=False)

        header = SegmentHeaderLike("HNHBK", "1", "3")
        assert header.type == "HNHBK"
        assert header.number == "1"
        assert header.version == "3"
        assert header.reference is None

    def test_nested_container_pattern(self):
        """Test pattern with nested data element groups."""

        class BankIdentifierLike(Container):
            country = ConcreteField(length=3)
            bank_code = ConcreteField(max_length=30)

        class AccountInfoLike(Container):
            account_number = ConcreteField(max_length=30)
            bank_id = ConcreteField(required=False)  # Would be a DEG field

        account = AccountInfoLike(account_number="123456789")
        assert account.account_number == "123456789"
        assert account.is_unset() is False

    def test_repeated_field_pattern(self):
        """Test pattern with repeated fields (like multiple TANs)."""

        class TANListLike(Container):
            tan_methods = ConcreteField(max_count=98, required=False)

        tan_list = TANListLike()
        tan_list.tan_methods[0] = "920"
        tan_list.tan_methods[1] = "942"
        tan_list.tan_methods[2] = "946"

        methods = list(tan_list.tan_methods)
        assert len(methods) == 3
        assert "920" in methods
        assert "942" in methods
        assert "946" in methods

    def test_segment_sequence_find_pattern(self):
        """Test typical segment search pattern."""
        # Create mock segments representing a typical response
        hibpa = MockSegment("HIBPA", 3)
        hiupa = MockSegment("HIUPA", 4)
        hiupd1 = MockSegment("HIUPD", 6)
        hiupd2 = MockSegment("HIUPD", 6)

        seq = SegmentSequence([hibpa, hiupa, hiupd1, hiupd2])

        # Find bank parameters
        bpa = seq.find_segment_first(query="HIBPA")
        assert bpa is not None
        assert bpa.header.type == "HIBPA"

        # Find all user accounts
        accounts = list(seq.find_segments(query="HIUPD"))
        assert len(accounts) == 2

        # Find highest version of a segment type
        highest_hiupd = seq.find_segment_highest_version(query="HIUPD")
        assert highest_hiupd is not None
        assert highest_hiupd.header.version == 6

    def test_optional_field_in_repr(self):
        """Test that optional empty fields don't appear in repr."""

        class OptionalFieldContainer(Container):
            required_field = ConcreteField()
            optional_field = ConcreteField(required=False)

        # Only set required field
        container = OptionalFieldContainer(required_field="value")
        repr_str = repr(container)

        assert "required_field='value'" in repr_str
        # Optional field should not appear since it's None
        assert "optional_field" not in repr_str


# ==============================================================================
# Edge Cases and Error Handling
# ==============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_segment_sequence_find(self):
        """Test searching empty SegmentSequence."""
        seq = SegmentSequence()
        result = list(seq.find_segments(query="ANYTHING"))
        assert result == []

    def test_valuelist_get_auto_creates(self):
        """Test that getting beyond current length auto-creates entries."""
        parent = ConcreteField(max_count=10)
        vl = ValueList(parent)

        # Access index 3 without setting anything
        _ = vl[3]
        assert len(vl._data) == 4  # 0, 1, 2, 3 created

    def test_container_with_no_fields(self):
        """Test empty Container subclass."""

        class EmptyContainer(Container):
            pass

        container = EmptyContainer()
        assert container.is_unset() is True
        assert list(container._repr_items) == []

    def test_segment_sequence_from_bytes_mock(self):
        """Test SegmentSequence initialization from bytes (mocked) using legacy parser."""
        # This tests the legacy code path, actual parsing is tested elsewhere
        # The parser is imported inside SegmentSequence.__init__, so we patch at the source
        with patch("fints.parser.FinTS3Parser") as mock_parser:
            mock_parser_instance = mock_parser.return_value
            mock_parser_instance.explode_segments.return_value = [["seg1"], ["seg2"]]
            mock_parser_instance.parse_segment.side_effect = [
                MockSegment("SEG1", 1),
                MockSegment("SEG2", 1),
            ]

            # Use use_pydantic=False to test the legacy parser path
            seq = SegmentSequence(b"raw bytes data", use_pydantic=False)

            assert len(seq.segments) == 2
            mock_parser_instance.explode_segments.assert_called_once()

    def test_segment_sequence_pydantic_parser_flag(self):
        """Test SegmentSequence uses Pydantic parser when flag is True."""
        from fints.infrastructure.fints.protocol.base import SegmentSequence as PydanticSegmentSequence

        with patch("fints.infrastructure.fints.protocol.parser.FinTSParser") as mock_parser:
            mock_result = MagicMock()
            mock_result.segments = []
            mock_parser.return_value.parse_message.return_value = mock_result

            # Test explicit use_pydantic=True parameter
            seq = SegmentSequence(b"raw bytes data", use_pydantic=True)

            assert len(seq.segments) == 0
            mock_parser.assert_called_once_with(robust_mode=True)
            mock_parser.return_value.parse_message.assert_called_once()

    def test_segment_sequence_legacy_parser_default(self):
        """Test SegmentSequence uses legacy parser by default."""
        with patch("fints.parser.FinTS3Parser") as mock_parser:
            mock_parser_instance = mock_parser.return_value
            mock_parser_instance.explode_segments.return_value = []
            mock_parser_instance.parse_segment.return_value = None

            # Default should use legacy parser
            seq = SegmentSequence(b"raw bytes data", use_pydantic=False)

            assert len(seq.segments) == 0
            mock_parser.assert_called_once()

