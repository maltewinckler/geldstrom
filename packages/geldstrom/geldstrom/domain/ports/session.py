"""Session lifecycle management independent of connector technology."""

from __future__ import annotations

from typing import Any, Protocol

from geldstrom.domain import SessionToken


class SessionPort(Protocol):
    """Open, refresh and close authenticated sessions."""

    def open_session(
        self,
        credentials: Any,
        state: SessionToken | None = None,
    ) -> SessionToken:
        """Authenticate and return a resumable session snapshot."""

    def refresh_session(self, state: SessionToken) -> SessionToken:
        """Refresh backend-specific state while keeping credentials external."""

    def close_session(self, state: SessionToken) -> None:
        """Terminate server-side sessions when explicit logout is required."""
