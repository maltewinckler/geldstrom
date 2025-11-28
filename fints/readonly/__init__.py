"""Read-only client exports.

Note: This module is maintained for backward compatibility.
New code should import from `fints` or `fints.clients` directly:

    from fints import ReadOnlyFinTSClient
    # or
    from fints.clients import ReadOnlyFinTSClient
"""
from fints.clients.readonly import ReadOnlyFinTSClient

__all__ = ["ReadOnlyFinTSClient"]
