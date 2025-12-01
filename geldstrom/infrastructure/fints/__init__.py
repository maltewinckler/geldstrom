"""FinTS-specific infrastructure helpers and constants."""
from .operations import FinTSOperations
from .responses import (
    DATA_BLOB_MAGIC_RETRY,
    NeedRetryResponse,
)
from .session import FinTSSessionState, SessionState

# Adapters are lazily imported to avoid circular dependencies
# Import them directly from geldstrom.infrastructure.fints.adapters when needed

# Debug utilities - import explicitly when needed:
#   from geldstrom.infrastructure.fints.debug import ParserDebugger, analyze_segments

__all__ = [
    "DATA_BLOB_MAGIC_RETRY",
    "FinTSOperations",
    "FinTSSessionState",
    "NeedRetryResponse",
    "SessionState",  # Backward compatibility alias
]
