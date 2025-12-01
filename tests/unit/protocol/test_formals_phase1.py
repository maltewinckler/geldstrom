"""Unit tests for Phase 1 DEG migrations.

Tests cover:
- TAN DEGs (tan.py)
- Transaction DEGs (transactions.py)
- Parameter DEGs (parameters.py)
"""
from __future__ import annotations

from datetime import date, time
from decimal import Decimal

import pytest

from fints.infrastructure.fints.protocol.formals import (
    # TAN DEGs
    TANMedia4,
    TANMedia5,
    ChallengeValidUntil,
    ParameterChallengeClass,
    ResponseHHDUC,
    TwoStepTANSubmission,
    # Transaction DEGs
    SupportedMessageTypes,
    BookedCamtStatements,
    SupportedSEPAPainMessages,
    BatchTransferParameter,
    ScheduledDebitParameter1,
    ScheduledDebitParameter2,
    QueryScheduledDebitParameter1,
    # Parameter DEGs
    SupportedLanguages,
    SupportedHBCIVersions,
    CommunicationParameter,
    AccountLimit,
    AllowedTransaction,
    AccountInformation,
    GetSEPAAccountParameter,
    # Enums
    TANMediaClass,
    TANMediumStatus,
    Language,
    ServiceType,
    # Identifiers
    BankIdentifier,
    AccountIdentifier,
)


# =============================================================================
# TAN DEG Tests
# =============================================================================


class TestTANMedia:
    """Tests for TAN media DEGs."""

    def test_tan_media4_creation(self):
        """Create TANMedia4 with minimal fields."""
        media = TANMedia4(
            tan_medium_class=TANMediaClass.MOBILE,
            status=TANMediumStatus.ACTIVE,
        )
        assert media.tan_medium_class == TANMediaClass.MOBILE
        assert media.status == TANMediumStatus.ACTIVE

    def test_tan_media5_creation(self):
        """Create TANMedia5 with security function."""
        media = TANMedia5(
            tan_medium_class=TANMediaClass.GENERATOR,
            status=TANMediumStatus.AVAILABLE,
            security_function=920,
            tan_medium_name="chipTAN",
        )
        assert media.security_function == 920
        assert media.tan_medium_name == "chipTAN"

    def test_tan_media_full(self):
        """Create TAN media with all fields."""
        bank_id = BankIdentifier(country_identifier="280", bank_code="12345678")
        account = AccountIdentifier(
            account_number="1234567890",
            subaccount_number="00",
            bank_identifier=bank_id,
        )

        media = TANMedia5(
            tan_medium_class=TANMediaClass.MOBILE,
            status=TANMediumStatus.ACTIVE,
            account=account,
            valid_from=date(2020, 1, 1),
            valid_until=date(2025, 12, 31),
            tan_medium_name="Mein Handy",
            mobile_number_masked="+49 170 ***1234",
            number_free_tans=50,
            last_use=date(2023, 12, 1),
        )
        assert media.valid_from == date(2020, 1, 1)
        assert media.number_free_tans == 50


class TestChallengeDegs:
    """Tests for challenge-related DEGs."""

    def test_challenge_valid_until(self):
        """Create ChallengeValidUntil."""
        challenge = ChallengeValidUntil(
            date=date(2023, 12, 25),
            time=time(14, 30, 0),
        )
        assert challenge.date == date(2023, 12, 25)
        assert challenge.time == time(14, 30, 0)

    def test_parameter_challenge_class(self):
        """Create ParameterChallengeClass."""
        params = ParameterChallengeClass(
            parameters=["param1", "param2", "param3"],
        )
        assert len(params.parameters) == 3

    def test_response_hhduc(self):
        """Create ResponseHHDUC."""
        response = ResponseHHDUC(
            atc="12345",
            ac=b"\x01\x02\x03\x04",
            ef_id_data=b"\x05\x06\x07\x08",
            cvr=b"\x09\x0a",
            version_info_chiptan=b"\x0b\x0c\x0d",
        )
        assert response.atc == "12345"
        assert len(response.ac) == 4


# =============================================================================
# Transaction DEG Tests
# =============================================================================


class TestTransactionDegs:
    """Tests for transaction-related DEGs."""

    def test_supported_message_types(self):
        """Create SupportedMessageTypes."""
        types = SupportedMessageTypes(
            expected_type=[
                "urn:iso:std:iso:20022:tech:xsd:camt.052.001.02",
                "urn:iso:std:iso:20022:tech:xsd:camt.053.001.02",
            ],
        )
        assert len(types.expected_type) == 2
        assert "camt.052" in types.expected_type[0]

    def test_booked_camt_statements(self):
        """Create BookedCamtStatements."""
        statements = BookedCamtStatements(
            statements=[b"<XML>...</XML>", b"<XML>...</XML>"],
        )
        assert len(statements.statements) == 2

    def test_supported_sepa_pain_messages(self):
        """Create SupportedSEPAPainMessages."""
        messages = SupportedSEPAPainMessages(
            sepa_descriptors=[
                "urn:iso:std:iso:20022:tech:xsd:pain.001.003.03",
            ],
        )
        assert "pain.001" in messages.sepa_descriptors[0]

    def test_batch_transfer_parameter(self):
        """Create BatchTransferParameter."""
        param = BatchTransferParameter(
            max_transfer_count=1000,
            sum_amount_required=True,
            single_booking_allowed=False,
        )
        assert param.max_transfer_count == 1000
        assert param.sum_amount_required is True

    def test_scheduled_debit_parameter1(self):
        """Create ScheduledDebitParameter1."""
        param = ScheduledDebitParameter1(
            min_advance_notice_FNAL_RCUR=2,
            max_advance_notice_FNAL_RCUR=14,
            min_advance_notice_FRST_OOFF=5,
            max_advance_notice_FRST_OOFF=14,
        )
        assert param.min_advance_notice_FNAL_RCUR == 2
        assert param.max_advance_notice_FRST_OOFF == 14

    def test_scheduled_debit_parameter2(self):
        """Create ScheduledDebitParameter2."""
        param = ScheduledDebitParameter2(
            min_advance_notice="D+2",
            max_advance_notice="D+14",
            allowed_purpose_codes="SALA,PENS",
        )
        assert param.min_advance_notice == "D+2"

    def test_query_scheduled_debit_parameter(self):
        """Create QueryScheduledDebitParameter."""
        param = QueryScheduledDebitParameter1(
            date_range_allowed=True,
            max_number_responses_allowed=True,
        )
        assert param.date_range_allowed is True


# =============================================================================
# Parameter DEG Tests
# =============================================================================


class TestParameterDegs:
    """Tests for BPD/UPD parameter DEGs."""

    def test_supported_languages(self):
        """Create SupportedLanguages."""
        langs = SupportedLanguages(
            languages=[Language.DE, Language.EN],
        )
        assert len(langs.languages) == 2
        assert Language.DE in langs.languages

    def test_supported_hbci_versions(self):
        """Create SupportedHBCIVersions."""
        versions = SupportedHBCIVersions(
            versions=["300", "220"],
        )
        assert len(versions.versions) == 2

    def test_communication_parameter(self):
        """Create CommunicationParameter."""
        param = CommunicationParameter(
            service_type=ServiceType.HTTPS,
            address="https://fints.example.com/fints",
        )
        assert param.service_type == ServiceType.HTTPS
        assert "https://" in param.address

    def test_communication_parameter_full(self):
        """Create CommunicationParameter with all fields."""
        param = CommunicationParameter(
            service_type=ServiceType.HTTPS,
            address="https://fints.example.com/fints",
            address_adjunct="/v2",
            filter_function="MIM",
            filter_function_version=1,
        )
        assert param.filter_function == "MIM"

    def test_account_limit(self):
        """Create AccountLimit."""
        limit = AccountLimit(
            limit_type="E",
            limit_amount=10000,
            limit_currency="EUR",
            limit_days=1,
        )
        assert limit.limit_amount == 10000

    def test_allowed_transaction(self):
        """Create AllowedTransaction."""
        tx = AllowedTransaction(
            transaction_code="HKSAL",
            required_signatures=1,
        )
        assert tx.transaction_code == "HKSAL"

    def test_allowed_transaction_with_limit(self):
        """Create AllowedTransaction with limit."""
        limit = AccountLimit(limit_amount=5000)
        tx = AllowedTransaction(
            transaction_code="HKCCS",
            required_signatures=1,
            limit=limit,
        )
        assert tx.limit.limit_amount == 5000

    def test_account_information(self):
        """Create AccountInformation."""
        bank_id = BankIdentifier(country_identifier="280", bank_code="12345678")
        info = AccountInformation(
            account_number="1234567890",
            bank_identifier=bank_id,
            customer_id="CUSTOMER123",
            account_holder_name_1="Max Mustermann",
            account_currency="EUR",
        )
        assert info.account_number == "1234567890"
        assert info.customer_id == "CUSTOMER123"

    def test_get_sepa_account_parameter(self):
        """Create GetSEPAAccountParameter."""
        param = GetSEPAAccountParameter(
            single_account_query_allowed=True,
            national_account_allowed=False,
        )
        assert param.single_account_query_allowed is True
        assert param.national_account_allowed is False

