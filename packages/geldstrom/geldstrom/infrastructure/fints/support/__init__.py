"""Cross-cutting operational concerns for FinTS infrastructure.

Connection lifecycle, serialization, and shared helpers that are used
across adapters but are not adapter implementations themselves.
"""

from .connection import ConnectionContext, FinTSConnectionHelper
from .helpers import account_key, locate_sepa_account
from .serialization import compress_datablob, decompress_datablob

__all__ = [
    "ConnectionContext",
    "FinTSConnectionHelper",
    "account_key",
    "compress_datablob",
    "decompress_datablob",
    "locate_sepa_account",
]
