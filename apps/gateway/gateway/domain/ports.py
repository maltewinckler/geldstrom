"""Gateway domain root ports.

BankingClient lives here (not inside banking/ or session/) because it
crosses both sub-domains: it accepts banking value objects and returns
session value objects (FetchResult, PendingChallenge).

Sub-domain-specific ports live closer to their domain:
  gateway.domain.banking.ports.repository  — BankDirectoryRepository
  gateway.domain.session.ports.repository  — ChallengeRepository
  gateway.domain.session.ports.services    — ApiKeyValidator, AuditEventPublisher
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from gateway.domain.banking.value_objects.connection import BankConnection, BankEndpoint
from gateway.domain.banking.value_objects.transaction import TransactionFetch
from gateway.domain.session.entities.pending_challenge import PendingChallenge

# Re-export sub-domain ports for convenience so callers can import everything
# from gateway.domain.ports if they prefer a single import point.
from gateway.domain.session.ports.services import ApiKeyValidator, AuditEventPublisher
from gateway.domain.session.value_objects.fetch_result import FetchResult

__all__ = [
    "ApiKeyValidator",
    "AuditEventPublisher",
    "BankingClient",
]


@runtime_checkable
class BankingClient(Protocol):
    """Protocol-agnostic banking client port.

    Receives a resolved BankEndpoint per request.
    Protocol-specific credentials (e.g., FinTS product_id) are read from
    the BankEndpoint, which is populated from Admin gRPC.
    """

    async def fetch_transactions(
        self,
        connection: BankConnection,
        endpoint: BankEndpoint,
        fetch: TransactionFetch,
    ) -> FetchResult: ...

    async def resume_with_tan(
        self,
        challenge: PendingChallenge,
        tan_response: str,
        endpoint: BankEndpoint,
    ) -> FetchResult: ...
