"""Application-layer use cases for the Gateway.

Orchestrates domain logic without infrastructure concerns.
All persistence and protocol dispatch is delegated through domain ports.
"""

from __future__ import annotations

from datetime import UTC, datetime

from gateway.domain.banking.ports.repository import BankDirectoryRepository
from gateway.domain.banking.value_objects.connection import BankConnection
from gateway.domain.banking.value_objects.transaction import TransactionFetch
from gateway.domain.dispatch import ProtocolDispatcher
from gateway.domain.exceptions import BankNotSupportedError, SessionNotFoundError
from gateway.domain.session.ports.repository import ChallengeRepository
from gateway.domain.session.value_objects.fetch_result import FetchResult, FetchStatus
from gateway.domain.session.value_objects.session_identity import SessionIdentity


class FetchTransactionsUseCase:
    """Orchestrates the transaction fetch workflow."""

    def __init__(
        self,
        dispatcher: ProtocolDispatcher,
        challenge_repo: ChallengeRepository,
        bank_directory: BankDirectoryRepository,
    ) -> None:
        self.dispatcher = dispatcher
        self.challenge_repo = challenge_repo
        self.bank_directory = bank_directory

    async def execute_initial(
        self,
        connection: BankConnection,
        fetch: TransactionFetch,
    ) -> FetchResult:
        """Initial fetch — resolve endpoint, dispatch to client."""
        endpoint = await self.bank_directory.resolve(
            connection.bank_code, connection.protocol
        )
        if endpoint is None:
            raise BankNotSupportedError(connection.bank_code, connection.protocol)

        client = self.dispatcher.get_client(connection.protocol)
        result = await client.fetch_transactions(connection, endpoint, fetch)

        if result.status == FetchStatus.CHALLENGE_REQUIRED and result.pending_challenge:
            await self.challenge_repo.save(result.pending_challenge)

        return result

    async def execute_resume(
        self,
        session_id: str,
        tan_response: str,
    ) -> FetchResult:
        """Resume a parked session with a TAN."""
        # Create a SessionIdentity with a dummy expires_at for lookup purposes.
        # The repository uses only session_id as the key; actual expiry is
        # managed by Redis TTL.
        identity = SessionIdentity(
            session_id=session_id,
            expires_at=datetime.now(UTC),
        )
        challenge = await self.challenge_repo.get(identity)
        if challenge is None:
            raise SessionNotFoundError(session_id)

        # Look up the endpoint to get protocol-specific credentials
        endpoint = await self.bank_directory.resolve(
            challenge.bank_code, challenge.protocol
        )
        if endpoint is None:
            raise BankNotSupportedError(challenge.bank_code, challenge.protocol)

        client = self.dispatcher.get_client(challenge.protocol)
        result = await client.resume_with_tan(challenge, tan_response, endpoint)
        await self.challenge_repo.delete(identity)
        return result
