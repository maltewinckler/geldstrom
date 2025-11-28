"""Read-only client module.

Note: This module is maintained for backward compatibility.
New code should import from `fints` or `fints.clients` directly.
"""
from fints.clients.readonly import ReadOnlyFinTSClient

__all__ = ["ReadOnlyFinTSClient"]
