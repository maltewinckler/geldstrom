"""FinTS 3.0 implementation of SessionPort."""
from __future__ import annotations

import logging

from fints.application.ports import GatewayCredentials
from fints.domain.ports.session import SessionPort
from fints.infrastructure.fints.session import FinTSSessionState

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

    def refresh_session(
        self,
        state: FinTSSessionState,
    ) -> FinTSSessionState:
        """
        Refresh session state (e.g., after BPD/UPD changes).

        Note: This requires credentials, which are not stored in state.
        For now, this raises NotImplementedError. Use open_session with
        existing state instead.
        """
        raise NotImplementedError(
            "refresh_session requires credentials. Use open_session with existing state."
        )

    def close_session(self, state: FinTSSessionState) -> None:
        """
        Close the session.

        Note: FinTS sessions don't require explicit server-side cleanup
        for read-only operations. This is a no-op for now.
        """
        # FinTS sessions don't require explicit logout for read operations
        pass


__all__ = ["FinTSSessionAdapter"]
