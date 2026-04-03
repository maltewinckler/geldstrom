"""FinTS 3.0 implementation of SessionPort."""

from __future__ import annotations

import logging

from geldstrom.domain.connection import ChallengeHandler, TANConfig
from geldstrom.domain.ports.session import SessionPort
from geldstrom.infrastructure.fints.credentials import GatewayCredentials
from geldstrom.infrastructure.fints.session import FinTSSessionState

from .connection import FinTSConnectionHelper

logger = logging.getLogger(__name__)


class FinTSSessionAdapter(SessionPort):
    """FinTS 3.0 implementation of SessionPort."""

    def __init__(
        self,
        *,
        tan_config: TANConfig | None = None,
        challenge_handler: ChallengeHandler | None = None,
    ) -> None:
        self._tan_config = tan_config or TANConfig()
        self._challenge_handler = challenge_handler

    def open_session(
        self,
        credentials: GatewayCredentials,
        state: FinTSSessionState | None = None,
    ) -> FinTSSessionState:
        helper = FinTSConnectionHelper(
            credentials,
            tan_config=self._tan_config,
            challenge_handler=self._challenge_handler,
        )

        with helper.connect(state) as ctx:
            logger.info(
                "Session opened: BPD v%d, UPD v%d",
                ctx.parameters.bpd_version,
                ctx.parameters.upd_version,
            )
            return helper.create_session_state(ctx)

    def refresh_session(self, state: FinTSSessionState) -> FinTSSessionState:
        """No-op: FinTS has no lightweight refresh; use open_session() to refresh parameters."""
        logger.debug(
            "refresh_session called but FinTS has no lightweight refresh; "
            "returning existing state. Use open_session() to refresh parameters."
        )
        return state

    def close_session(self, state: FinTSSessionState) -> None:
        # FinTS read-only operations don't require explicit logout.
        pass


__all__ = ["FinTSSessionAdapter"]
