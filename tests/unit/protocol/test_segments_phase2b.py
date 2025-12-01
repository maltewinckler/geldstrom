"""Unit tests for Phase 2b Segment migrations.

Tests cover:
- Bank segments (bank.py)
- PIN/TAN parameter segments (pintan.py)
"""
from __future__ import annotations

import pytest

from fints.infrastructure.fints.protocol.segments import (
    # Bank segments
    HIBPA3,
    HIUPA4,
    HIUPD6,
    HKKOM4,
    HIKOM4,
    # PIN/TAN segments
    HIPINS1,
    HITANS6,
    HITANS7,
    # DEGs
    TransactionTANRequired,
    ParameterPinTan,
    TwoStepParameters6,
    TwoStepParameters7,
    ParameterTwostepTAN6,
    ParameterTwostepTAN7,
)
from fints.infrastructure.fints.protocol.formals import (
    BankIdentifier,
    Language,
    UPDUsage,
    CommunicationParameter,
    ServiceType,
    AccountLimit,
    AllowedTransaction,
)
from fints.infrastructure.fints.protocol.base import SegmentHeader


# =============================================================================
# Bank Segment Tests
# =============================================================================


class TestBankParameterSegments:
    """Tests for bank parameter segments."""

    def test_hibpa3_creation(self):
        """Create bank parameter segment."""
        bank_id = BankIdentifier(country_identifier="280", bank_code="12345678")

        seg = HIBPA3(
            header=SegmentHeader(type="HIBPA", version=3, number=3),
            bpd_version=17,
            bank_identifier=bank_id,
            bank_name="Test Bank AG",
            number_tasks=5,
            supported_languages=[Language.DE, Language.EN],
            supported_hbci_versions=["300"],
        )
        assert seg.SEGMENT_TYPE == "HIBPA"
        assert seg.bpd_version == 17
        assert seg.bank_name == "Test Bank AG"
        assert len(seg.supported_languages) == 2

    def test_hibpa3_with_optional_fields(self):
        """Create bank parameter segment with all fields."""
        bank_id = BankIdentifier(country_identifier="280", bank_code="12345678")

        seg = HIBPA3(
            header=SegmentHeader(type="HIBPA", version=3, number=3),
            bpd_version=17,
            bank_identifier=bank_id,
            bank_name="Test Bank AG",
            number_tasks=5,
            supported_languages=[Language.DE],
            supported_hbci_versions=["300"],
            max_message_length=9999,
            min_timeout=30,
            max_timeout=300,
        )
        assert seg.max_message_length == 9999
        assert seg.min_timeout == 30

    def test_hiupa4_creation(self):
        """Create user parameter segment."""
        seg = HIUPA4(
            header=SegmentHeader(type="HIUPA", version=4, number=4),
            user_identifier="USERID123",
            upd_version=5,
            upd_usage=UPDUsage.UPD_CONCLUSIVE,
        )
        assert seg.SEGMENT_TYPE == "HIUPA"
        assert seg.user_identifier == "USERID123"

    def test_hiupa4_with_username(self):
        """Create user parameter segment with username."""
        seg = HIUPA4(
            header=SegmentHeader(type="HIUPA", version=4, number=4),
            user_identifier="USERID123",
            upd_version=5,
            upd_usage=UPDUsage.UPD_INCONCLUSIVE,
            username="Max Mustermann",
        )
        assert seg.username == "Max Mustermann"

    def test_hiupd6_creation(self):
        """Create account information segment."""
        seg = HIUPD6(
            header=SegmentHeader(type="HIUPD", version=6, number=5),
            iban="DE89370400440532013000",
            customer_id="CUST123",
            account_type=1,
            account_currency="EUR",
            name_account_owner_1="Max Mustermann",
        )
        assert seg.SEGMENT_TYPE == "HIUPD"
        assert seg.iban == "DE89370400440532013000"
        assert seg.account_currency == "EUR"

    def test_hiupd6_with_allowed_transactions(self):
        """Create account information with allowed transactions."""
        tx = AllowedTransaction(
            transaction_code="HKSAL",
            required_signatures=1,
        )
        seg = HIUPD6(
            header=SegmentHeader(type="HIUPD", version=6, number=5),
            iban="DE89370400440532013000",
            customer_id="CUST123",
            account_type=1,
            account_currency="EUR",
            name_account_owner_1="Max Mustermann",
            allowed_transactions=[tx],
        )
        assert len(seg.allowed_transactions) == 1
        assert seg.allowed_transactions[0].transaction_code == "HKSAL"


class TestCommunicationSegments:
    """Tests for communication segments."""

    def test_hkkom4_creation(self):
        """Create communication request segment."""
        seg = HKKOM4(
            header=SegmentHeader(type="HKKOM", version=4, number=3),
        )
        assert seg.SEGMENT_TYPE == "HKKOM"

    def test_hkkom4_with_filters(self):
        """Create communication request with filters."""
        bank_id = BankIdentifier(country_identifier="280", bank_code="12345678")
        seg = HKKOM4(
            header=SegmentHeader(type="HKKOM", version=4, number=3),
            start_bank_identifier=bank_id,
            max_number_responses=100,
        )
        assert seg.start_bank_identifier.bank_code == "12345678"

    def test_hikom4_creation(self):
        """Create communication response segment."""
        bank_id = BankIdentifier(country_identifier="280", bank_code="12345678")
        comm_param = CommunicationParameter(
            service_type=ServiceType.HTTPS,
            address="https://fints.example.com/fints",
        )

        seg = HIKOM4(
            header=SegmentHeader(type="HIKOM", version=4, number=4),
            bank_identifier=bank_id,
            default_language=Language.DE,
            communication_parameters=[comm_param],
        )
        assert seg.SEGMENT_TYPE == "HIKOM"
        assert len(seg.communication_parameters) == 1


# =============================================================================
# PIN/TAN Parameter Segment Tests
# =============================================================================


class TestPinTanDegs:
    """Tests for PIN/TAN DEGs."""

    def test_transaction_tan_required(self):
        """Create TransactionTANRequired."""
        tx = TransactionTANRequired(
            transaction="HKCCS",
            tan_required=True,
        )
        assert tx.transaction == "HKCCS"
        assert tx.tan_required is True

    def test_parameter_pintan(self):
        """Create ParameterPinTan."""
        param = ParameterPinTan(
            min_pin_length=5,
            max_pin_length=20,
            max_tan_length=6,
        )
        assert param.min_pin_length == 5
        assert param.max_tan_length == 6

    def test_parameter_pintan_with_transactions(self):
        """Create ParameterPinTan with transaction list."""
        tx_list = [
            TransactionTANRequired(transaction="HKSAL", tan_required=False),
            TransactionTANRequired(transaction="HKCCS", tan_required=True),
        ]
        param = ParameterPinTan(
            transaction_tans_required=tx_list,
        )
        assert len(param.transaction_tans_required) == 2

    def test_twostep_parameters6(self):
        """Create TwoStepParameters6."""
        from fints.infrastructure.fints.protocol.formals.enums import TANTimeDialogAssociation

        param = TwoStepParameters6(
            security_function="920",
            tan_process="2",
            technical_id="pushTAN-dec",
            name="pushTAN",
            max_length_input=6,
            tan_time_dialog_association=TANTimeDialogAssociation.ALLOWED,
        )
        assert param.security_function == "920"
        assert param.name == "pushTAN"

    def test_twostep_parameters7(self):
        """Create TwoStepParameters7 with decoupled fields."""
        param = TwoStepParameters7(
            security_function="921",
            tan_process="S",
            technical_id="pushTAN-dec",
            name="pushTAN 2.0",
            decoupled_max_poll_number=10,
            wait_before_first_poll=5,
            wait_before_next_poll=2,
            manual_confirmation_allowed=True,
            automated_polling_allowed=False,
        )
        assert param.decoupled_max_poll_number == 10


class TestPinTanSegments:
    """Tests for PIN/TAN parameter segments."""

    def test_hipins1_creation(self):
        """Create HIPINS1 segment."""
        param = ParameterPinTan(
            min_pin_length=5,
            max_pin_length=20,
        )
        seg = HIPINS1(
            header=SegmentHeader(type="HIPINS", version=1, number=5),
            max_number_tasks=1,
            min_number_signatures=0,
            security_class=0,
            parameter=param,
        )
        assert seg.SEGMENT_TYPE == "HIPINS"
        assert seg.parameter.min_pin_length == 5

    def test_hitans6_creation(self):
        """Create HITANS6 segment."""
        from fints.infrastructure.fints.protocol.formals.enums import TaskHashAlgorithm

        twostep = TwoStepParameters6(
            security_function="920",
            tan_process="2",
            technical_id="pushTAN",
        )
        param = ParameterTwostepTAN6(
            one_step_allowed=False,
            multiple_tasks_allowed=False,
            task_hash_algorithm=TaskHashAlgorithm.NONE,
            twostep_parameters=[twostep],
        )
        seg = HITANS6(
            header=SegmentHeader(type="HITANS", version=6, number=6),
            max_number_tasks=1,
            min_number_signatures=1,
            security_class=0,
            parameter=param,
        )
        assert seg.SEGMENT_TYPE == "HITANS"
        assert len(seg.parameter.twostep_parameters) == 1

    def test_hitans7_creation(self):
        """Create HITANS7 segment."""
        from fints.infrastructure.fints.protocol.formals.enums import TaskHashAlgorithm

        twostep = TwoStepParameters7(
            security_function="921",
            tan_process="S",
            technical_id="decoupled",
            decoupled_max_poll_number=10,
        )
        param = ParameterTwostepTAN7(
            one_step_allowed=False,
            multiple_tasks_allowed=False,
            task_hash_algorithm=TaskHashAlgorithm.NONE,
            twostep_parameters=[twostep],
        )
        seg = HITANS7(
            header=SegmentHeader(type="HITANS", version=7, number=7),
            max_number_tasks=1,
            min_number_signatures=1,
            security_class=0,
            parameter=param,
        )
        assert seg.SEGMENT_TYPE == "HITANS"
        assert seg.parameter.twostep_parameters[0].decoupled_max_poll_number == 10

    def test_hitans7_multiple_tan_methods(self):
        """Create HITANS7 with multiple TAN methods."""
        from fints.infrastructure.fints.protocol.formals.enums import TaskHashAlgorithm

        methods = [
            TwoStepParameters7(
                security_function="920",
                tan_process="2",
                technical_id="smsTAN",
                name="smsTAN",
            ),
            TwoStepParameters7(
                security_function="921",
                tan_process="S",
                technical_id="pushTAN",
                name="pushTAN",
                decoupled_max_poll_number=10,
            ),
        ]
        param = ParameterTwostepTAN7(
            one_step_allowed=False,
            multiple_tasks_allowed=False,
            task_hash_algorithm=TaskHashAlgorithm.NONE,
            twostep_parameters=methods,
        )
        seg = HITANS7(
            header=SegmentHeader(type="HITANS", version=7, number=7),
            max_number_tasks=1,
            min_number_signatures=1,
            security_class=0,
            parameter=param,
        )
        assert len(seg.parameter.twostep_parameters) == 2
        assert seg.parameter.twostep_parameters[0].name == "smsTAN"
        assert seg.parameter.twostep_parameters[1].name == "pushTAN"

