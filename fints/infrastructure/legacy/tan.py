"""Legacy TAN handling - re-exports from new auth module.

DEPRECATED: Import from `fints.infrastructure.fints.auth` instead.

This module is kept for backward compatibility only.
"""
from __future__ import annotations

import warnings

from fints.infrastructure.fints.auth.challenge import NeedTANResponse
from fints.infrastructure.fints.auth.workflow import IMPLEMENTED_HKTAN_VERSIONS

# Emit deprecation warning when this module is imported directly
warnings.warn(
    "fints.infrastructure.legacy.tan is deprecated. "
    "Import from fints.infrastructure.fints.auth instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["NeedTANResponse", "IMPLEMENTED_HKTAN_VERSIONS"]
