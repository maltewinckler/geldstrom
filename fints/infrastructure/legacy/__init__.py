"""Legacy FinTS infrastructure helpers used by the classic client.

Note: TAN-related classes are now provided by the new auth module at
`fints.infrastructure.fints.auth`. This module re-exports them for
backward compatibility. New code should import directly from the auth module.
"""
from __future__ import annotations

from .dialog_manager import DialogSessionManager
from .touchdown import TouchdownPaginator

# Re-export from new auth module for backward compatibility
# Import directly to avoid deprecation warnings in legacy wrapper files
from fints.infrastructure.fints.auth.challenge import NeedTANResponse
from fints.infrastructure.fints.auth.workflow import (
    IMPLEMENTED_HKTAN_VERSIONS,
    PinTanWorkflow,
)

__all__ = [
    "DialogSessionManager",
    "IMPLEMENTED_HKTAN_VERSIONS",
    "NeedTANResponse",
    "PinTanWorkflow",
    "TouchdownPaginator",
]
