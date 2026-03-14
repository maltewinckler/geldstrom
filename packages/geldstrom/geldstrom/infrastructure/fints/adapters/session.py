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
    """
    FinTS 3.0 implementation of the SessionPort.

    Handles session lifecycle: opening authenticated dialogs,
    refreshing state, and closing sessions.
    """

    def __init__(
        self,
        *,
        tan_config: TANConfig | None = None,
        challenge_handler: ChallengeHandler | None = None,
    ) -> None:
        """
        Initialize the session adapter.

        Args:
            tan_config: Configuration for TAN handling (polling, timeout)
            challenge_handler: Handler for presenting 2FA challenges to user
        """
        self._tan_config = tan_config or TANConfig()
        self._challenge_handler = challenge_handler

    def open_session(
        self,
        credentials: GatewayCredentials,
        state: FinTSSessionState | None = None,
    ) -> FinTSSessionState:
        """
        Open a FinTS session and return resumable state.

        Args:
            credentials: Bank connection credentials
            state: Optional existing session state to resume

        Returns:
            New or refreshed FinTSSessionState
        """
        helper = FinTSConnectionHelper(
            credentials,
            tan_config=self._tan_config,
            challenge_handler=self._challenge_handler,
        )

        with helper.connect(state) as ctx:
            # Dialog is initialized, BPD/UPD should be populated
            logger.info(
                "Session opened: BPD v%d, UPD v%d",
                ctx.parameters.bpd_version,
                ctx.parameters.upd_version,
            )
            return helper.create_session_state(ctx)

    def refresh_session(self, state: FinTSSessionState) -> FinTSSessionState:
        """
        Refresh session state (no-op for FinTS).

        FinTS sessions don't have a lightweight refresh mechanism. The BPD/UPD
        parameters are fetched during dialog initialization, and refreshing
        them requires a full re-authentication with credentials.

        For FinTS, use `open_session(credentials, state)` instead to refresh
        parameters while preserving the system_id.

        Args:
            state: Current session state

        Returns:
            The same session state (unchanged)
        """
        logger.debug(
            "refresh_session called but FinTS has no lightweight refresh; "
            "returning existing state. Use open_session() to refresh parameters."
        )
        return state

    def close_session(self, state: FinTSSessionState) -> None:
        """
        Close the session.

        Note: FinTS sessions don't require explicit server-side cleanup
        for read-only operations. This is a no-op for now.
        """
        # FinTS sessions don't require explicit logout for read operations
        pass


__all__ = ["FinTSSessionAdapter"]
