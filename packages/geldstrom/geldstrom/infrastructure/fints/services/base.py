"""Base class for FinTS 3.0 services with shared connection boilerplate."""

from __future__ import annotations

from geldstrom.infrastructure.fints.challenge import ChallengeHandler, TANConfig
from geldstrom.infrastructure.fints.credentials import GatewayCredentials
from geldstrom.infrastructure.fints.support.connection import FinTSConnectionHelper


class FinTSServiceBase:
    """Shared initialisation and helper-construction for FinTS services."""

    def __init__(
        self,
        credentials: GatewayCredentials,
        *,
        tan_config: TANConfig | None = None,
        challenge_handler: ChallengeHandler | None = None,
    ) -> None:
        self._credentials = credentials
        self._tan_config = tan_config or TANConfig()
        self._challenge_handler = challenge_handler

    def _make_helper(self) -> FinTSConnectionHelper:
        return FinTSConnectionHelper(
            self._credentials,
            tan_config=self._tan_config,
            challenge_handler=self._challenge_handler,
        )
