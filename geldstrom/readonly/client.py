"""Read-only client module.

Note: This module is maintained for backward compatibility.
New code should import from `fints` or `fints.clients` directly.
"""
from geldstrom.clients.readonly import ReadOnlyFinTSClient

__all__ = ["ReadOnlyFinTSClient"]
