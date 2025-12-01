"""Unit tests for Phase 2 Segment migrations.

Tests cover:
- Dialog segments (dialog.py)
- Message segments (message.py)
- Auth segments (auth.py)
"""
from __future__ import annotations

from datetime import date, time

import pytest

from fints.infrastructure.fints.protocol.segments import (
    # Dialog segments
    HNHBK3,
    HNHBS1,
    HIRMG2,
    HIRMS2,
    HKSYN3,
    HISYN4,
    HKEND1,
    # Message segments
    HNVSK3,
    HNVSD1,
    HNSHK4,
    HNSHA2,
    # Auth segments
    HKIDN2,
    HKVVB3,
    HKTAN2,
    HKTAN6,
    HKTAN7,
    HITAN6,
    HITAN7,
    HKTAB4,
    HKTAB5,
    HITAB4,
    HITAB5,
)
from fints.infrastructure.fints.protocol.formals import (
    BankIdentifier,
    Response,
    ReferenceMessage,
    SynchronizationMode,
    SecurityProfile,
    SecurityMethod,
    SecurityRole,
    SecurityIdentificationDetails,
    SecurityDateTime,
    EncryptionAlgorithm,
    HashAlgorithm,
    SignatureAlgorithm,
    KeyName,
    KeyType,
    UserDefinedSignature,
    CompressionFunction,
    SecurityApplicationArea,
    IdentifiedRole,
    DateTimeType,
    UsageEncryption,
    OperationMode,
    EncryptionAlgorithmCoded,
    AlgorithmParameterName,
    AlgorithmParameterIVName,
    SystemIDStatus,
    Language,
    TANMediaType,
    TANMediaClass,
    TANMediumStatus,
    TANUsageOption,
    TANMedia4,
    TANMedia5,
)
from fints.infrastructure.fints.protocol.base import SegmentHeader


# =============================================================================
# Dialog Segment Tests
# =============================================================================


class TestDialogSegments:
    """Tests for dialog management segments."""

    def test_hnhbk3_creation(self):
        """Create message header segment."""
        seg = HNHBK3(
            header=SegmentHeader(type="HNHBK", version=3, number=1),
            message_size=123,
            hbci_version=300,
            dialog_id="0",
            message_number=1,
        )
        assert seg.SEGMENT_TYPE == "HNHBK"
        assert seg.message_size == 123
        assert seg.hbci_version == 300

    def test_hnhbk3_with_reference(self):
        """Create message header with reference message."""
        ref = ReferenceMessage(dialog_id="123", message_number=2)
        seg = HNHBK3(
            header=SegmentHeader(type="HNHBK", version=3, number=1),
            message_size=456,
            hbci_version=300,
            dialog_id="123",
            message_number=3,
            reference_message=ref,
        )
        assert seg.reference_message.dialog_id == "123"

    def test_hnhbs1_creation(self):
        """Create message trailer segment."""
        seg = HNHBS1(
            header=SegmentHeader(type="HNHBS", version=1, number=99),
            message_number=1,
        )
        assert seg.SEGMENT_TYPE == "HNHBS"
        assert seg.message_number == 1

    def test_hirmg2_creation(self):
        """Create global message response."""
        responses = [
            Response(code="0010", reference_element="", text="Nachricht entgegengenommen"),
        ]
        seg = HIRMG2(
            header=SegmentHeader(type="HIRMG", version=2, number=2),
            responses=responses,
        )
        assert len(seg.responses) == 1
        assert seg.responses[0].code == "0010"

    def test_hirms2_creation(self):
        """Create segment response."""
        responses = [
            Response(code="0010", reference_element="3", text="Verarbeitung OK"),
            Response(code="3040", reference_element="4", text="Fortsetzung"),
        ]
        seg = HIRMS2(
            header=SegmentHeader(type="HIRMS", version=2, number=3),
            responses=responses,
        )
        assert len(seg.responses) == 2

    def test_hksyn3_creation(self):
        """Create synchronization request."""
        seg = HKSYN3(
            header=SegmentHeader(type="HKSYN", version=3, number=3),
            synchronization_mode=SynchronizationMode.NEW_SYSTEM_ID,
        )
        assert seg.synchronization_mode == SynchronizationMode.NEW_SYSTEM_ID

    def test_hisyn4_creation(self):
        """Create synchronization response."""
        seg = HISYN4(
            header=SegmentHeader(type="HISYN", version=4, number=4),
            system_id="system123",
        )
        assert seg.system_id == "system123"

    def test_hkend1_creation(self):
        """Create dialog end segment."""
        seg = HKEND1(
            header=SegmentHeader(type="HKEND", version=1, number=5),
            dialog_id="dialog456",
        )
        assert seg.dialog_id == "dialog456"


# =============================================================================
# Message Security Segment Tests
# =============================================================================


class TestMessageSecuritySegments:
    """Tests for message security segments."""

    def test_hnvsk3_creation(self):
        """Create encryption header."""
        bank_id = BankIdentifier(country_identifier="280", bank_code="12345678")

        seg = HNVSK3(
            header=SegmentHeader(type="HNVSK", version=3, number=998),
            security_profile=SecurityProfile(
                security_method=SecurityMethod.PIN,
                security_method_version=1,
            ),
            security_function="998",
            security_role=SecurityRole.ISS,
            security_identification_details=SecurityIdentificationDetails(
                identified_role=IdentifiedRole.MS,
                identifier="0",
            ),
            security_datetime=SecurityDateTime(
                date_time_type=DateTimeType.STS,
                date=date(2023, 12, 25),
                time=time(14, 30),
            ),
            encryption_algorithm=EncryptionAlgorithm(
                usage_encryption=UsageEncryption.OSY,
                operation_mode=OperationMode.CBC,
                encryption_algorithm=EncryptionAlgorithmCoded.TWOKEY3DES,
                algorithm_parameter_value=b"\x00" * 8,
                algorithm_parameter_name=AlgorithmParameterName.KYE,
                algorithm_parameter_iv_name=AlgorithmParameterIVName.IVC,
            ),
            key_name=KeyName(
                bank_identifier=bank_id,
                user_id="testuser",
                key_type=KeyType.V,
                key_number=0,
                key_version=0,
            ),
            compression_function=CompressionFunction.NULL,
        )
        assert seg.SEGMENT_TYPE == "HNVSK"
        assert seg.security_profile.security_method == SecurityMethod.PIN

    def test_hnvsd1_creation(self):
        """Create encrypted data container."""
        seg = HNVSD1(
            header=SegmentHeader(type="HNVSD", version=1, number=999),
            data=b"@123@encrypted_content_here",
        )
        assert seg.SEGMENT_TYPE == "HNVSD"
        assert b"encrypted_content" in seg.data

    def test_hnshk4_creation(self):
        """Create signature header."""
        bank_id = BankIdentifier(country_identifier="280", bank_code="12345678")

        seg = HNSHK4(
            header=SegmentHeader(type="HNSHK", version=4, number=2),
            security_profile=SecurityProfile(
                security_method=SecurityMethod.PIN,
                security_method_version=1,
            ),
            security_function="999",
            security_reference="12345678901234",
            security_application_area=SecurityApplicationArea.SHT,
            security_role=SecurityRole.ISS,
            security_identification_details=SecurityIdentificationDetails(
                identified_role=IdentifiedRole.MS,
                identifier="system123",
            ),
            security_reference_number=1,
            security_datetime=SecurityDateTime(
                date_time_type=DateTimeType.STS,
            ),
            hash_algorithm=HashAlgorithm(
                usage_hash="1",
                hash_algorithm="999",
                algorithm_parameter_name="1",
            ),
            signature_algorithm=SignatureAlgorithm(
                usage_signature="6",
                signature_algorithm="10",
                operation_mode="16",
            ),
            key_name=KeyName(
                bank_identifier=bank_id,
                user_id="testuser",
                key_type=KeyType.S,
                key_number=0,
                key_version=0,
            ),
        )
        assert seg.SEGMENT_TYPE == "HNSHK"

    def test_hnsha2_creation(self):
        """Create signature trailer."""
        seg = HNSHA2(
            header=SegmentHeader(type="HNSHA", version=2, number=5),
            security_reference="12345678901234",
            user_defined_signature=UserDefinedSignature(
                pin="12345",
            ),
        )
        assert seg.user_defined_signature.pin == "12345"


# =============================================================================
# Auth Segment Tests
# =============================================================================


class TestAuthSegments:
    """Tests for authentication segments."""

    def test_hkidn2_creation(self):
        """Create identification segment."""
        bank_id = BankIdentifier(country_identifier="280", bank_code="12345678")
        seg = HKIDN2(
            header=SegmentHeader(type="HKIDN", version=2, number=3),
            bank_identifier=bank_id,
            customer_id="customer123",
            system_id="system456",
            system_id_status=SystemIDStatus.ID_UNNECESSARY,
        )
        assert seg.customer_id == "customer123"

    def test_hkvvb3_creation(self):
        """Create processing preparation segment."""
        seg = HKVVB3(
            header=SegmentHeader(type="HKVVB", version=3, number=4),
            bpd_version=0,
            upd_version=0,
            language=Language.DE,
            product_name="python-fints",
            product_version="1.0",
        )
        assert seg.product_name == "python-fints"
        assert seg.language == Language.DE

    def test_hktan2_creation(self):
        """Create TAN request segment v2."""
        seg = HKTAN2(
            header=SegmentHeader(type="HKTAN", version=2, number=5),
            tan_process="4",
        )
        assert seg.tan_process == "4"

    def test_hktan6_creation(self):
        """Create TAN request segment v6."""
        seg = HKTAN6(
            header=SegmentHeader(type="HKTAN", version=6, number=5),
            tan_process="4",
            segment_type="HKSAL",
            tan_medium_name="MyDevice",
        )
        assert seg.segment_type == "HKSAL"
        assert seg.tan_medium_name == "MyDevice"

    def test_hktan7_creation(self):
        """Create TAN request segment v7."""
        seg = HKTAN7(
            header=SegmentHeader(type="HKTAN", version=7, number=5),
            tan_process="S",
            task_reference="ref12345",
        )
        assert seg.tan_process == "S"
        assert seg.task_reference == "ref12345"

    def test_hitan6_creation(self):
        """Create TAN response segment v6."""
        seg = HITAN6(
            header=SegmentHeader(type="HITAN", version=6, number=6),
            tan_process="4",
            challenge="Please approve in your app",
            tan_medium_name="MyPhone",
        )
        assert seg.challenge == "Please approve in your app"

    def test_hitan7_creation(self):
        """Create TAN response segment v7."""
        seg = HITAN7(
            header=SegmentHeader(type="HITAN", version=7, number=6),
            tan_process="S",
            task_reference="order12345",
            challenge="Bitte in App freigeben",
        )
        assert seg.task_reference == "order12345"


class TestTANMediaSegments:
    """Tests for TAN media segments."""

    def test_hktab4_creation(self):
        """Create TAN media list request v4."""
        seg = HKTAB4(
            header=SegmentHeader(type="HKTAB", version=4, number=3),
            tan_media_type=TANMediaType.ACTIVE,
            tan_media_class=TANMediaClass.ALL,
        )
        assert seg.tan_media_type == TANMediaType.ACTIVE

    def test_hktab5_creation(self):
        """Create TAN media list request v5."""
        seg = HKTAB5(
            header=SegmentHeader(type="HKTAB", version=5, number=3),
            tan_media_type=TANMediaType.ALL,
            tan_media_class=TANMediaClass.MOBILE,
        )
        assert seg.tan_media_class == TANMediaClass.MOBILE

    def test_hitab4_creation(self):
        """Create TAN media list response v4."""
        media = TANMedia4(
            tan_medium_class=TANMediaClass.MOBILE,
            status=TANMediumStatus.ACTIVE,
            tan_medium_name="iPhone",
        )
        seg = HITAB4(
            header=SegmentHeader(type="HITAB", version=4, number=4),
            tan_usage_option=TANUsageOption.ALL_ACTIVE,
            tan_media_list=[media],
        )
        assert len(seg.tan_media_list) == 1
        assert seg.tan_media_list[0].tan_medium_name == "iPhone"

    def test_hitab5_creation(self):
        """Create TAN media list response v5."""
        media = TANMedia5(
            tan_medium_class=TANMediaClass.GENERATOR,
            status=TANMediumStatus.AVAILABLE,
            security_function=920,
            tan_medium_name="chipTAN QR",
        )
        seg = HITAB5(
            header=SegmentHeader(type="HITAB", version=5, number=4),
            tan_usage_option=TANUsageOption.EXACTLY_ONE,
            tan_media_list=[media],
        )
        assert seg.tan_media_list[0].security_function == 920

