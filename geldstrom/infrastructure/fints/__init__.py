"""FinTS-specific infrastructure helpers and constants."""

from .operations import FinTSOperations
from .session import FinTSSessionState, SessionState

# Adapters are lazily imported to avoid circular dependencies
# Import them directly from geldstrom.infrastructure.fints.adapters when needed

# Debug utilities - import explicitly when needed:
#   from geldstrom.infrastructure.fints.debug import ParserDebugger, analyze_segments

__all__ = [
    "FinTSOperations",
    "FinTSSessionState",
    "SessionState",  # Backward compatibility alias
]
