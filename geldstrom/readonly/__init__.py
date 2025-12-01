"""Read-only client exports.

Note: This module is maintained for backward compatibility.
New code should import from `fints` or `fints.clients` directly:

    from geldstrom import ReadOnlyFinTSClient
    # or
    from geldstrom.clients import ReadOnlyFinTSClient
"""
from geldstrom.clients.readonly import ReadOnlyFinTSClient

__all__ = ["ReadOnlyFinTSClient"]
