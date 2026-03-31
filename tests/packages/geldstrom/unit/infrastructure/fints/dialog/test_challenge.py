"""Unit tests for FinTSChallenge."""

from __future__ import annotations

from dataclasses import dataclass

from geldstrom.domain.connection.challenge import ChallengeType
from geldstrom.infrastructure.fints.dialog.challenge import FinTSChallenge


@dataclass
class MockHITAN:
    """Mock HITAN segment for testing."""

    task_reference: str | None = None
    challenge: str | None = None
    challenge_hhduc: bytes | None = None


class TestFinTSChallenge:
    """Tests for FinTSChallenge wrapper."""

    def test_decoupled_challenge_from_hitan(self) -> None:
        """Decoupled challenge should be detected from HITAN with task_reference only."""
        hitan = MockHITAN(
            task_reference="REF123",
            challenge="Please confirm in your banking app",
        )

        challenge = FinTSChallenge(hitan)

        assert challenge.is_decoupled is True
        assert challenge.challenge_type == ChallengeType.DECOUPLED
        assert challenge.challenge_text == "Please confirm in your banking app"
        assert challenge.challenge_data is None
        assert challenge.task_reference == "REF123"

    def test_flicker_challenge_from_hitan(self) -> None:
        """Flicker challenge should be detected from HITAN with HHD_UC data."""
        hitan = MockHITAN(
            task_reference="REF456",
            challenge="Enter TAN from device",
            challenge_hhduc=b"FLICKER_DATA",
        )

        challenge = FinTSChallenge(hitan)

        assert challenge.is_decoupled is False
        assert challenge.challenge_type == ChallengeType.FLICKER
        assert challenge.challenge_text == "Enter TAN from device"
        assert challenge.challenge_data is not None
        assert challenge.challenge_data.mime_type == "application/x-hhduc"
        assert challenge.challenge_data.data == b"FLICKER_DATA"

    def test_text_challenge_from_hitan(self) -> None:
        """Text challenge should be detected from HITAN without task_reference or HHD_UC."""
        hitan = MockHITAN(
            challenge="Enter TAN from letter",
        )

        challenge = FinTSChallenge(hitan)

        assert challenge.is_decoupled is False
        assert challenge.challenge_type == ChallengeType.TEXT
        assert challenge.challenge_text == "Enter TAN from letter"
        assert challenge.challenge_data is None

    def test_get_data_returns_task_reference(self) -> None:
        """get_data should return serialized task reference."""
        hitan = MockHITAN(task_reference="REF789")

        challenge = FinTSChallenge(hitan)

        assert challenge.get_data() == b"REF789"

    def test_get_data_empty_when_no_reference(self) -> None:
        """get_data should return empty bytes when no task reference."""
        hitan = MockHITAN()

        challenge = FinTSChallenge(hitan)

        assert challenge.get_data() == b""

    def test_challenge_html_not_supported(self) -> None:
        """HTML challenge text should not be supported in FinTS."""
        hitan = MockHITAN(challenge="Some text")

        challenge = FinTSChallenge(hitan)

        assert challenge.challenge_html is None
