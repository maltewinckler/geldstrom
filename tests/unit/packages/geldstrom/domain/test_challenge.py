"""Unit tests for TANConfig and challenge handling."""

from __future__ import annotations

import pytest

from geldstrom.domain.connection.challenge import (
    Challenge,
    ChallengeData,
    ChallengeHandler,
    ChallengeResult,
    ChallengeType,
    InteractiveChallengeHandler,
    TANConfig,
)


class TestTANConfig:
    """Tests for TANConfig Pydantic model."""

    def test_default_values(self) -> None:
        """Default values should be reasonable for decoupled TAN."""
        config = TANConfig()
        assert config.poll_interval == 2.0
        assert config.timeout_seconds == 120.0

    def test_custom_values(self) -> None:
        """Custom values should be accepted."""
        config = TANConfig(poll_interval=5.0, timeout_seconds=300.0)
        assert config.poll_interval == 5.0
        assert config.timeout_seconds == 300.0

    def test_poll_interval_cannot_exceed_timeout(self) -> None:
        """poll_interval cannot exceed timeout_seconds."""
        with pytest.raises(ValueError, match="poll_interval cannot exceed timeout"):
            TANConfig(poll_interval=10.0, timeout_seconds=5.0)

    def test_is_pydantic_model(self) -> None:
        """TANConfig should be a Pydantic model for consistency."""
        from pydantic import BaseModel

        assert issubclass(TANConfig, BaseModel)


class TestChallengeResult:
    """Tests for ChallengeResult dataclass."""

    def test_success_with_response(self) -> None:
        """Result with response should indicate success."""
        result = ChallengeResult(response="123456")
        assert result.is_success is True
        assert result.needs_polling is False

    def test_cancelled_not_success(self) -> None:
        """Cancelled result should not indicate success."""
        result = ChallengeResult(cancelled=True)
        assert result.is_success is False
        assert result.needs_polling is False

    def test_error_not_success(self) -> None:
        """Result with error should not indicate success."""
        result = ChallengeResult(error="Something went wrong")
        assert result.is_success is False
        assert result.needs_polling is False

    def test_needs_polling_for_decoupled(self) -> None:
        """Empty result should indicate polling needed (decoupled flow)."""
        result = ChallengeResult()
        assert result.is_success is False
        assert result.needs_polling is True


class MockDecoupledChallenge(Challenge):
    """Mock challenge for testing."""

    def __init__(
        self,
        *,
        is_decoupled: bool = True,
        text: str = "Please confirm in your banking app",
    ) -> None:
        self._is_decoupled = is_decoupled
        self._text = text

    @property
    def challenge_type(self) -> ChallengeType:
        return ChallengeType.DECOUPLED if self._is_decoupled else ChallengeType.TEXT

    @property
    def challenge_text(self) -> str | None:
        return self._text

    @property
    def challenge_html(self) -> str | None:
        return None

    @property
    def challenge_data(self) -> ChallengeData | None:
        return None

    @property
    def is_decoupled(self) -> bool:
        return self._is_decoupled

    def get_data(self) -> bytes:
        return b""


class TestInteractiveChallengeHandler:
    """Tests for InteractiveChallengeHandler."""

    def test_decoupled_challenge_returns_needs_polling(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Decoupled challenge should print message and return needs_polling."""
        handler = InteractiveChallengeHandler()
        challenge = MockDecoupledChallenge()

        result = handler.present_challenge(challenge)

        assert result.needs_polling is True
        assert result.cancelled is False
        assert result.response is None

        captured = capsys.readouterr()
        assert "Please confirm in your banking app" in captured.out


class RecordingChallengeHandler:
    """Test double that records challenge presentations."""

    def __init__(self, result: ChallengeResult | None = None) -> None:
        self.presented_challenges: list[Challenge] = []
        self._result = result or ChallengeResult()

    def present_challenge(self, challenge: Challenge) -> ChallengeResult:
        self.presented_challenges.append(challenge)
        return self._result


class TestChallengeHandlerProtocol:
    """Tests for ChallengeHandler protocol compliance."""

    def test_recording_handler_satisfies_protocol(self) -> None:
        """RecordingChallengeHandler should satisfy ChallengeHandler protocol."""
        handler = RecordingChallengeHandler()
        # Protocol check via isinstance with runtime_checkable
        assert isinstance(handler, ChallengeHandler)

    def test_interactive_handler_satisfies_protocol(self) -> None:
        """InteractiveChallengeHandler should satisfy ChallengeHandler protocol."""
        handler = InteractiveChallengeHandler()
        assert isinstance(handler, ChallengeHandler)
