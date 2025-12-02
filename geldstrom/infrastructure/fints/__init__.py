"""FinTS-specific infrastructure helpers and constants."""

from .credentials import GatewayCredentials
from .exceptions import (
    FinTSClientError,
    FinTSClientPINError,
    FinTSClientTemporaryAuthError,
    FinTSConnectionError,
    FinTSDialogError,
    FinTSDialogInitError,
    FinTSDialogOfflineError,
    FinTSDialogStateError,
    FinTSError,
    FinTSNoResponseError,
    FinTSSCARequiredError,
    FinTSUnsupportedOperation,
)
from .operations import FinTSOperations
from .session import FinTSSessionState, SessionState

# Adapters are lazily imported to avoid circular dependencies
# Import them directly from geldstrom.infrastructure.fints.adapters when needed

# Debug utilities - import explicitly when needed:
#   from geldstrom.infrastructure.fints.debug import ParserDebugger, analyze_segments

__all__ = [
    "FinTSClientError",
    "FinTSClientPINError",
    "FinTSClientTemporaryAuthError",
    "FinTSConnectionError",
    "FinTSDialogError",
    "FinTSDialogInitError",
    "FinTSDialogOfflineError",
    "FinTSDialogStateError",
    "FinTSError",
    "FinTSNoResponseError",
    "FinTSOperations",
    "FinTSSCARequiredError",
    "FinTSSessionState",
    "FinTSUnsupportedOperation",
    "GatewayCredentials",
    "SessionState",  # Backward compatibility alias
]
