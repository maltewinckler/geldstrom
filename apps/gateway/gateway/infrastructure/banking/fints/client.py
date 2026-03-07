"""FinTS banking client adapter.

Implements the BankingClient port by wrapping the geldstrom FinTS3Client.
Maps between gateway domain models and geldstrom domain models.
All synchronous FinTS3Client calls are wrapped in asyncio.to_thread().

FinTS product credentials (product_id, product_version, country_code) are
read from the BankEndpoint value object, which is populated from the Admin
gRPC GetBankEndpoint response. This allows per-bank product credentials.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from gateway.domain.banking.value_objects.connection import (
    BankConnection,
    BankEndpoint,
    BankingProtocol,
)
from gateway.domain.banking.value_objects.transaction import (
    TransactionData,
    TransactionFetch,
)
from gateway.domain.exceptions import BankConnectionError, TANRejectedError
from gateway.domain.session.entities.pending_challenge import PendingChallenge
from gateway.domain.session.value_objects.fetch_result import (
    ChallengeInfo,
    FetchResult,
    FetchStatus,
)
from gateway.domain.session.value_objects.session_identity import SessionIdentity
from geldstrom.clients.fints3 import FinTS3Client
from geldstrom.domain.connection.challenge import Challenge, ChallengeResult
from geldstrom.domain.connection.credentials import BankCredentials
from geldstrom.domain.model.bank import BankRoute
from geldstrom.infrastructure.fints.credentials import GatewayCredentials
from geldstrom.infrastructure.fints.session import FinTSSessionState

if TYPE_CHECKING:
    from collections.abc import Sequence

    from geldstrom.domain.model.accounts import Account
    from geldstrom.domain.model.transactions import TransactionFeed

logger = logging.getLogger(__name__)


class _ChallengeSignal(Exception):
    """Internal signal raised when a TAN challenge is received."""

    def __init__(self, challenge: Challenge) -> None:
        self.challenge = challenge
        super().__init__("TAN challenge received")


class _ChallengeCapture:
    """ChallengeHandler that captures the challenge and raises _ChallengeSignal.

    Used during initial fetch to intercept TAN challenges so the adapter
    can serialize session state and return CHALLENGE_REQUIRED.
    """

    def present_challenge(self, challenge: Challenge) -> ChallengeResult:
        raise _ChallengeSignal(challenge)


class _TANSubmitter:
    """ChallengeHandler that immediately returns the pre-supplied TAN response.

    Used during resume_with_tan to automatically submit the TAN
    when the bank re-presents the challenge.
    """

    def __init__(self, tan_response: str) -> None:
        self._tan_response = tan_response

    def present_challenge(self, challenge: Challenge) -> ChallengeResult:
        return ChallengeResult(response=self._tan_response)


class MissingFinTSCredentialsError(Exception):
    """Raised when FinTS credentials are missing from BankEndpoint."""

    def __init__(self, bank_code: str, missing_field: str) -> None:
        self.bank_code = bank_code
        self.missing_field = missing_field
        super().__init__(
            f"Missing FinTS credential '{missing_field}' for bank {bank_code}"
        )


def _build_credentials(
    connection: BankConnection,
    endpoint: BankEndpoint,
) -> GatewayCredentials:
    """Map gateway domain models → geldstrom GatewayCredentials.

    Reads FinTS product credentials from BankEndpoint (populated from Admin gRPC).
    """
    # Validate required FinTS credentials are present
    if endpoint.fints_product_id is None:
        raise MissingFinTSCredentialsError(connection.bank_code, "fints_product_id")
    if endpoint.fints_product_version is None:
        raise MissingFinTSCredentialsError(
            connection.bank_code, "fints_product_version"
        )

    country_code = endpoint.fints_country_code or "DE"

    return GatewayCredentials(
        route=BankRoute(
            country_code=country_code,
            bank_code=connection.bank_code,
        ),
        server_url=endpoint.server_url,
        credentials=BankCredentials(
            user_id=connection.username.get_secret_value(),
            secret=connection.pin,
        ),
        product_id=endpoint.fints_product_id.get_secret_value(),
        product_version=endpoint.fints_product_version,
    )


def _map_transactions(feed: TransactionFeed) -> list[TransactionData]:
    """Map geldstrom TransactionFeed entries → gateway TransactionData list."""
    return [
        TransactionData(
            entry_id=entry.entry_id,
            booking_date=entry.booking_date,
            value_date=entry.value_date,
            amount=entry.amount,
            currency=entry.currency,
            purpose=entry.purpose,
            counterpart_name=entry.counterpart_name,
            counterpart_iban=entry.counterpart_iban,
            metadata=dict(entry.metadata),
        )
        for entry in feed.entries
    ]


def _find_account_by_iban(accounts: Sequence[Account], iban: str) -> Account | str:
    """Find an account by IBAN from the connected accounts list.

    Returns the Account if found, otherwise returns the IBAN string
    to let FinTS3Client attempt lookup by identifier.
    """
    for account in accounts:
        if account.iban == iban:
            return account
    return iban


class FinTSBankingClient:
    """Implements BankingClient port for FinTS protocol.

    Reads FinTS product credentials from BankEndpoint (populated from Admin gRPC).
    Wraps synchronous geldstrom FinTS3Client calls in asyncio.to_thread().
    """

    async def fetch_transactions(
        self,
        connection: BankConnection,
        endpoint: BankEndpoint,
        fetch: TransactionFetch,
    ) -> FetchResult:
        """Fetch transactions from a bank via FinTS.

        Creates a FinTS3Client, connects, and retrieves transactions.
        If the bank requires a TAN challenge, serializes the session state
        and returns CHALLENGE_REQUIRED with challenge info.

        FinTS product credentials are read from the BankEndpoint.
        """
        credentials = _build_credentials(connection, endpoint)
        bank_code = connection.bank_code

        def _sync_fetch() -> FetchResult:
            client = FinTS3Client.from_gateway_credentials(
                credentials,
                challenge_handler=_ChallengeCapture(),
            )
            try:
                accounts = client.connect()
                account = _find_account_by_iban(accounts, fetch.iban)
                feed = client.get_transactions(
                    account,
                    start_date=fetch.date_range.start,
                    end_date=fetch.date_range.end,
                )
                return FetchResult(
                    status=FetchStatus.SUCCESS,
                    transactions=_map_transactions(feed),
                )
            except _ChallengeSignal as sig:
                return _handle_challenge_signal(client, sig, bank_code)
            finally:
                try:
                    client.disconnect()
                except Exception:
                    logger.debug("Error during disconnect", exc_info=True)

        try:
            return await asyncio.to_thread(_sync_fetch)
        except _ChallengeSignal:
            raise  # pragma: no cover
        except BankConnectionError:
            raise
        except MissingFinTSCredentialsError:
            raise
        except Exception as exc:
            raise BankConnectionError(connection.bank_code, reason=str(exc)) from exc

    async def resume_with_tan(
        self,
        challenge: PendingChallenge,
        tan_response: str,
        endpoint: BankEndpoint,
    ) -> FetchResult:
        """Resume a parked FinTS session by submitting a TAN.

        Deserializes the dialog state from the PendingChallenge,
        creates a new FinTS3Client with that session state, and
        uses a _TANSubmitter handler to automatically provide the TAN.

        FinTS product credentials are read from the BankEndpoint.
        """
        session_state = FinTSSessionState.deserialize(challenge.dialog_state)

        # Validate required FinTS credentials are present
        if endpoint.fints_product_id is None:
            raise MissingFinTSCredentialsError(
                session_state.route.bank_code, "fints_product_id"
            )
        if endpoint.fints_product_version is None:
            raise MissingFinTSCredentialsError(
                session_state.route.bank_code, "fints_product_version"
            )

        credentials = GatewayCredentials(
            route=session_state.route,
            server_url="",  # Not needed for session resume
            credentials=BankCredentials(
                user_id=session_state.user_id,
                secret="resume-placeholder",
            ),
            product_id=endpoint.fints_product_id.get_secret_value(),
            product_version=endpoint.fints_product_version,
        )

        def _sync_resume() -> FetchResult:
            client = FinTS3Client.from_gateway_credentials(
                credentials,
                session_state=session_state,
                challenge_handler=_TANSubmitter(tan_response),
            )
            try:
                accounts = client.connect()
                if accounts:
                    feed = client.get_transactions(accounts[0])
                    return FetchResult(
                        status=FetchStatus.SUCCESS,
                        transactions=_map_transactions(feed),
                    )
                return FetchResult(status=FetchStatus.SUCCESS, transactions=[])
            except ValueError as exc:
                if "cancelled" in str(exc).lower() or "rejected" in str(exc).lower():
                    raise TANRejectedError(
                        challenge.identity.session_id, reason=str(exc)
                    ) from exc
                raise
            finally:
                try:
                    client.disconnect()
                except Exception:
                    logger.debug("Error during disconnect", exc_info=True)

        try:
            return await asyncio.to_thread(_sync_resume)
        except TANRejectedError:
            raise
        except MissingFinTSCredentialsError:
            raise
        except Exception as exc:
            raise TANRejectedError(
                challenge.identity.session_id, reason=str(exc)
            ) from exc


def _handle_challenge_signal(
    client: FinTS3Client,
    signal: _ChallengeSignal,
    bank_code: str,
) -> FetchResult:
    """Build a CHALLENGE_REQUIRED FetchResult from a captured challenge signal."""
    challenge = signal.challenge
    identity = SessionIdentity.create()

    session_token = client.session_state
    dialog_state = session_token.serialize() if session_token else b""

    media_data: bytes | None = None
    challenge_data = challenge.challenge_data
    if challenge_data is not None:
        media_data = challenge_data.data

    pending = PendingChallenge(
        identity=identity,
        protocol=BankingProtocol.FINTS,
        bank_code=bank_code,
        dialog_state=dialog_state,
        challenge_type=challenge.challenge_type.value,
        challenge_text=challenge.challenge_text,
        media_data=media_data,
    )

    return FetchResult(
        status=FetchStatus.CHALLENGE_REQUIRED,
        challenge=ChallengeInfo(
            session_id=identity.session_id,
            type=pending.challenge_type,
            media_data=media_data,
        ),
        pending_challenge=pending,
    )
