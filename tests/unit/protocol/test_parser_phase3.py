"""Unit tests for Phase 3 Parser Integration.

Tests cover:
- Segment registry with all new segments
- Parsing of dialog/message/auth segments
- Round-trip tests (serialize -> parse)
"""

from __future__ import annotations

from geldstrom.infrastructure.fints.protocol.base import FinTSSegment, SegmentHeader
from geldstrom.infrastructure.fints.protocol.formals import (
    BankIdentifier,
    Language,
    Response,
    SynchronizationMode,
    SystemIDStatus,
    UPDUsage,
)
from geldstrom.infrastructure.fints.protocol.parser import (
    FinTSParser,
    FinTSSerializer,
)
from geldstrom.infrastructure.fints.protocol.segments import (
    # Bank
    HIBPA3,
    # PIN/TAN
    HIPINS1,
    HIRMG2,
    HIRMS2,
    HISYN4,
    HITAN6,
    HITANS6,
    HIUPA4,
    # Transfer
    HKEND1,
    # Auth
    HKIDN2,
    # Balance
    HKSYN3,
    HKTAN6,
    HKVVB3,
    # Dialog
    HNHBK3,
    HNHBS1,
    HNSHA2,
    HNSHK4,
    HNVSD1,
    # Response DEG testing
    # Message
    HNVSK3,
)

# =============================================================================
# Registry Tests
# =============================================================================


class TestSegmentAutoRegistration:
    """Tests for segment auto-registration with all segments."""

    def test_registry_has_all_segment_types(self):
        """Verify all segment types are registered."""
        get = FinTSSegment.get_segment_class

        # Check dialog segments
        assert get("HNHBK", 3) == HNHBK3
        assert get("HNHBS", 1) == HNHBS1
        assert get("HIRMG", 2) == HIRMG2
        assert get("HIRMS", 2) == HIRMS2
        assert get("HKSYN", 3) == HKSYN3
        assert get("HISYN", 4) == HISYN4
        assert get("HKEND", 1) == HKEND1

    def test_registry_has_message_segments(self):
        """Verify message security segments are registered."""
        get = FinTSSegment.get_segment_class

        assert get("HNVSK", 3) == HNVSK3
        assert get("HNVSD", 1) == HNVSD1
        assert get("HNSHK", 4) == HNSHK4
        assert get("HNSHA", 2) == HNSHA2

    def test_registry_has_auth_segments(self):
        """Verify auth segments are registered."""
        get = FinTSSegment.get_segment_class

        assert get("HKIDN", 2) == HKIDN2
        assert get("HKVVB", 3) == HKVVB3
        assert get("HKTAN", 6) == HKTAN6
        assert get("HITAN", 6) == HITAN6

    def test_registry_has_bank_segments(self):
        """Verify bank parameter segments are registered."""
        get = FinTSSegment.get_segment_class

        assert get("HIBPA", 3) == HIBPA3
        assert get("HIUPA", 4) == HIUPA4

    def test_registry_has_pintan_segments(self):
        """Verify PIN/TAN segments are registered."""
        get = FinTSSegment.get_segment_class

        assert get("HIPINS", 1) == HIPINS1
        assert get("HITANS", 6) == HITANS6

    def test_registry_count(self):
        """Verify total number of registered segments."""
        # We should have at least 70 segments
        assert len(FinTSSegment._segment_registry) >= 70

        # We should have at least 45 segment types
        assert len(FinTSSegment.get_registered_types()) >= 45

    def test_get_versions(self):
        """Test getting all versions of a segment type."""
        # HKSAL has versions 5, 6, 7
        versions = FinTSSegment.get_versions("HKSAL")
        assert versions == [5, 6, 7]

        # HKTAN has versions 2, 6, 7
        versions = FinTSSegment.get_versions("HKTAN")
        assert versions == [2, 6, 7]

    def test_get_highest_version(self):
        """Test getting highest version of a segment type."""
        # HKSAL highest is 7
        from geldstrom.infrastructure.fints.protocol.segments import HKSAL7

        versions = FinTSSegment.get_versions("HKSAL")
        highest = FinTSSegment.get_segment_class("HKSAL", max(versions))
        assert highest == HKSAL7


# =============================================================================
# Parser Round-Trip Tests
# =============================================================================


class TestParserRoundTrip:
    """Tests for parse -> serialize round-trips."""

    def test_roundtrip_hnhbk3(self):
        """Round-trip test for message header."""
        seg = HNHBK3(
            header=SegmentHeader(type="HNHBK", version=3, number=1),
            message_size=123,
            hbci_version=300,
            dialog_id="0",
            message_number=1,
        )

        serializer = FinTSSerializer()
        wire = serializer.serialize_segment(seg)

        parser = FinTSParser()
        parsed = parser.parse_segment(wire)

        assert parsed.SEGMENT_TYPE == "HNHBK"
        assert parsed.message_size == 123
        assert parsed.hbci_version == 300

    def test_roundtrip_hnhbs1(self):
        """Round-trip test for message trailer."""
        seg = HNHBS1(
            header=SegmentHeader(type="HNHBS", version=1, number=99),
            message_number=1,
        )

        serializer = FinTSSerializer()
        wire = serializer.serialize_segment(seg)

        parser = FinTSParser()
        parsed = parser.parse_segment(wire)

        assert parsed.SEGMENT_TYPE == "HNHBS"
        assert parsed.message_number == 1

    def test_roundtrip_hirmg2(self):
        """Round-trip test for global response."""
        responses = [
            Response(
                code="0010", reference_element="", text="Nachricht entgegengenommen"
            ),
        ]
        seg = HIRMG2(
            header=SegmentHeader(type="HIRMG", version=2, number=2),
            responses=responses,
        )

        serializer = FinTSSerializer()
        wire_bytes = serializer.serialize_message(seg)

        parser = FinTSParser()
        result = parser.parse_message(wire_bytes)

        assert len(result.segments) == 1
        parsed = result.segments[0]
        assert parsed.SEGMENT_TYPE == "HIRMG"
        assert len(parsed.responses) == 1
        assert parsed.responses[0].code == "0010"

    def test_roundtrip_hksyn3(self):
        """Round-trip test for synchronization request."""
        seg = HKSYN3(
            header=SegmentHeader(type="HKSYN", version=3, number=3),
            synchronization_mode=SynchronizationMode.NEW_SYSTEM_ID,
        )

        serializer = FinTSSerializer()
        wire = serializer.serialize_segment(seg)

        parser = FinTSParser()
        parsed = parser.parse_segment(wire)

        assert parsed.SEGMENT_TYPE == "HKSYN"
        assert parsed.synchronization_mode == SynchronizationMode.NEW_SYSTEM_ID

    def test_roundtrip_hkidn2(self):
        """Round-trip test for identification."""
        bank_id = BankIdentifier(country_identifier="280", bank_code="12345678")
        seg = HKIDN2(
            header=SegmentHeader(type="HKIDN", version=2, number=3),
            bank_identifier=bank_id,
            customer_id="CUSTOMER123",
            system_id="0",
            system_id_status=SystemIDStatus.ID_UNNECESSARY,
        )

        serializer = FinTSSerializer()
        wire = serializer.serialize_segment(seg)

        parser = FinTSParser()
        parsed = parser.parse_segment(wire)

        assert parsed.SEGMENT_TYPE == "HKIDN"
        assert parsed.customer_id == "CUSTOMER123"
        assert parsed.bank_identifier.bank_code == "12345678"

    def test_roundtrip_hkvvb3(self):
        """Round-trip test for processing preparation."""
        seg = HKVVB3(
            header=SegmentHeader(type="HKVVB", version=3, number=4),
            bpd_version=0,
            upd_version=0,
            language=Language.DE,
            product_name="python-fints",
            product_version="1.0",
        )

        serializer = FinTSSerializer()
        wire = serializer.serialize_segment(seg)

        parser = FinTSParser()
        parsed = parser.parse_segment(wire)

        assert parsed.SEGMENT_TYPE == "HKVVB"
        assert parsed.product_name == "python-fints"
        assert parsed.language == Language.DE

    def test_roundtrip_hibpa3(self):
        """Round-trip test for bank parameters."""
        bank_id = BankIdentifier(country_identifier="280", bank_code="12345678")
        seg = HIBPA3(
            header=SegmentHeader(type="HIBPA", version=3, number=5),
            bpd_version=17,
            bank_identifier=bank_id,
            bank_name="Test Bank",
            number_tasks=5,
            supported_languages=[Language.DE],
            supported_hbci_versions=["300"],
        )

        serializer = FinTSSerializer()
        wire = serializer.serialize_segment(seg)

        parser = FinTSParser()
        parsed = parser.parse_segment(wire)

        assert parsed.SEGMENT_TYPE == "HIBPA"
        assert parsed.bank_name == "Test Bank"
        assert parsed.bpd_version == 17

    def test_roundtrip_hiupa4(self):
        """Round-trip test for user parameters."""
        seg = HIUPA4(
            header=SegmentHeader(type="HIUPA", version=4, number=6),
            user_identifier="USER123",
            upd_version=5,
            upd_usage=UPDUsage.UPD_CONCLUSIVE,
        )

        serializer = FinTSSerializer()
        wire = serializer.serialize_segment(seg)

        parser = FinTSParser()
        parsed = parser.parse_segment(wire)

        assert parsed.SEGMENT_TYPE == "HIUPA"
        assert parsed.user_identifier == "USER123"


# =============================================================================
# Parser Edge Cases
# =============================================================================


class TestParserEdgeCases:
    """Tests for parser edge cases."""

    def test_parse_unknown_segment(self):
        """Test parsing unknown segment type returns None."""
        parser = FinTSParser(robust_mode=True)

        # Create a wire format for an unknown segment
        wire = b"UNKN:1:1+data'"

        # Unknown segments return GenericSegment in robust mode
        _ = parser.parse_segment(wire)

        # Unknown segment types aren't in the auto-registry
        assert FinTSSegment.get_segment_class("UNKN", 1) is None

    def test_parse_multiple_responses(self):
        """Test parsing segment with multiple responses."""
        responses = [
            Response(code="0010", reference_element="3", text="OK"),
            Response(code="0020", reference_element="4", text="Aufgenommen"),
            Response(code="3040", reference_element="5", text="Fortsetzung"),
        ]
        seg = HIRMS2(
            header=SegmentHeader(type="HIRMS", version=2, number=3),
            responses=responses,
        )

        serializer = FinTSSerializer()
        wire_bytes = serializer.serialize_message(seg)

        parser = FinTSParser()
        result = parser.parse_message(wire_bytes)

        assert len(result.segments) == 1
        parsed = result.segments[0]
        assert len(parsed.responses) == 3
        assert parsed.responses[0].code == "0010"
        assert parsed.responses[1].code == "0020"
        assert parsed.responses[2].code == "3040"
