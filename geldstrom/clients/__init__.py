"""Client layer - public API for interacting with banks.

This module provides the main user-facing clients for FinTS operations.
Import clients directly from here or from the top-level `fints` package.

Example:
    from geldstrom.clients import FinTS3Client, ReadOnlyFinTSClient

    # Or from top level:
    from geldstrom import FinTS3Client
"""
from __future__ import annotations

from .base import ClientCredentials
from .fints3 import FinTS3Client
from .readonly import ReadOnlyFinTSClient

__all__ = [
    "ClientCredentials",
    "FinTS3Client",
    "ReadOnlyFinTSClient",
]

