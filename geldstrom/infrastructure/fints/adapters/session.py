"""FinTS 3.0 implementation of SessionPort."""
from __future__ import annotations

import logging

from geldstrom.application.ports import GatewayCredentials
from geldstrom.domain.ports.session import SessionPort
from geldstrom.infrastructure.fints.session import FinTSSessionState

from .connection import FinTSConnectionHelper

logger = logging.getLogger(__name__)


class FinTSSessionAdapter(SessionPort):
    """
    FinTS 3.0 implementation of the SessionPort.

    Handles session lifecycle: opening authenticated dialogs,
    refreshing state, and closing sessions.
    """

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
        helper = FinTSConnectionHelper(credentials)

        with helper.connect(state) as ctx:
            # Dialog is initialized, BPD/UPD should be populated
            logger.info(
                "Session opened: BPD v%d, UPD v%d",
                ctx.parameters.bpd_version,
                ctx.parameters.upd_version,
            )
            return helper.create_session_state(ctx)

    def close_session(self, state: FinTSSessionState) -> None:
        """
        Close the session.

        Note: FinTS sessions don't require explicit server-side cleanup
        for read-only operations. This is a no-op for now.
        """
        # FinTS sessions don't require explicit logout for read operations
        pass


__all__ = ["FinTSSessionAdapter"]
