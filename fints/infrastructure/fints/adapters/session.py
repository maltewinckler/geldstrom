"""FinTS 3.0 implementation of SessionPort."""
from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from fints.application.ports import GatewayCredentials
from fints.domain.ports.session import SessionPort
from fints.infrastructure.fints.session import FinTSSessionState

if TYPE_CHECKING:
    from fints.client import FinTS3PinTanClient


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
        client = self._build_client(credentials, state)
        with self._logged_in(client):
            # Trigger dialog initialization and information fetch
            client.get_information()
        return self._session_from_client(credentials, client)

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

    # --- Internal helpers ---

    def _build_client(
        self,
        credentials: GatewayCredentials,
        state: FinTSSessionState | None,
    ) -> "FinTS3PinTanClient":
        """Build a configured FinTS client."""
        from fints.client import FinTS3PinTanClient

        kwargs: dict[str, Any] = {
            "bank_identifier": credentials.route.bank_code,
            "user_id": credentials.user_id,
            "pin": credentials.pin,
            "server": credentials.server_url,
            "customer_id": credentials.customer_id or credentials.user_id,
            "product_id": credentials.product_id,
            "product_version": credentials.product_version,
            "tan_medium": credentials.tan_medium,
        }

        if state:
            kwargs["from_data"] = state.client_blob
            kwargs["system_id"] = state.system_id

        client = FinTS3PinTanClient(**kwargs)

        if credentials.tan_method:
            client.set_tan_mechanism(credentials.tan_method)

        return client

    @contextmanager
    def _logged_in(self, client: "FinTS3PinTanClient"):
        """Context manager for client login/logout."""
        with client:
            yield client

    def _session_from_client(
        self,
        credentials: GatewayCredentials,
        client: "FinTS3PinTanClient",
    ) -> FinTSSessionState:
        """Extract session state from an active client."""
        blob = client.deconstruct(including_private=True)
        return FinTSSessionState(
            route=credentials.route,
            user_id=credentials.user_id,
            system_id=client.system_id,
            client_blob=blob,
            bpd_version=client.bpd_version,
            upd_version=client.upd_version,
        )


__all__ = ["FinTSSessionAdapter"]

