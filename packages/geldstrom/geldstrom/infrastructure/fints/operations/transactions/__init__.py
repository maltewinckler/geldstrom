"""Transaction history operations split by wire format.

- mt940: HKKAZ → MT940 byte decode → domain TransactionFeed
- camt:  HKCAZ → CAMT XML parse → domain TransactionFeed
"""

from .camt import CamtFetcher
from .camt import parse_approved_response as parse_camt_approved_response
from .mt940 import Mt940Fetcher, mt940_to_array
from .mt940 import parse_approved_response as parse_mt940_approved_response

__all__ = [
    "CamtFetcher",
    "Mt940Fetcher",
    "mt940_to_array",
    "parse_camt_approved_response",
    "parse_mt940_approved_response",
]
