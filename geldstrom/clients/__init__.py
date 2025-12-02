"""Client layer - public API for interacting with banks.

This module provides the main user-facing clients for FinTS operations.
Import clients directly from here or from the top-level `geldstrom` package.

Example:
    from geldstrom.clients import FinTS3Client

    # Or from top level:
    from geldstrom import FinTS3Client
"""

from __future__ import annotations

from .fints3 import FinTS3Client

__all__ = [
    "FinTS3Client",
]
