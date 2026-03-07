"""FinTS protocol configuration — infrastructure concern.

FinTSProtocolConfig is intentionally NOT in the domain layer because it
carries FinTS-specific operational parameters that are meaningless outside
the FinTS infrastructure adapter.

NOTE: FinTS product credentials (product_id, product_version, country_code)
are now provided per-bank via the Admin gRPC GetBankEndpoint response and
stored in the BankEndpoint value object. This config file is kept for
potential future FinTS-specific settings that are not per-bank.
"""

from __future__ import annotations

from pydantic import BaseModel

from gateway.domain.banking.value_objects.connection import BankingProtocol


class FinTSProtocolConfig(BaseModel, frozen=True):
    """FinTS-specific configuration loaded at application startup.

    NOTE: Product credentials (product_id, product_version, country_code)
    have been moved to BankEndpoint and are now provided per-bank via
    the Admin gRPC GetBankEndpoint response.
    """

    protocol: BankingProtocol
