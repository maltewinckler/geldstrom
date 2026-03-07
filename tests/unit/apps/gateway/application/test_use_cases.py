"""Unit tests for FetchTransactionsUseCase."""

# ruff: noqa: D103
import datetime as _dt
import types as _types
from unittest.mock import AsyncMock  # noqa: F401 - used in fixtures below

import pytest  # noqa: F401 - used in fixtures and tests below

import gateway.application.use_cases as _uc  # noqa: F401
import gateway.domain.dispatch as _disp  # noqa: F401
import gateway.domain.exceptions as _exc  # noqa: F401

# Aggregate domain types under a single namespace to keep test helpers readable
_m = _types.SimpleNamespace()

from gateway.domain.banking.value_objects.connection import (  # noqa: E402
    BankConnection,
    BankEndpoint,
    BankingProtocol,
)
from gateway.domain.banking.value_objects.transaction import (  # noqa: E402
    DateRange,
    TransactionData,
    TransactionFetch,
)
from gateway.domain.session.entities.pending_challenge import (
    PendingChallenge,  # noqa: E402
)
from gateway.domain.session.value_objects.fetch_result import (  # noqa: E402
    ChallengeInfo,
    FetchResult,
    FetchStatus,
)
from gateway.domain.session.value_objects.session_identity import (
    SessionIdentity,  # noqa: E402
)

_m.BankConnection = BankConnection
_m.BankEndpoint = BankEndpoint
_m.BankingProtocol = BankingProtocol
_m.DateRange = DateRange
_m.TransactionData = TransactionData
_m.TransactionFetch = TransactionFetch
_m.PendingChallenge = PendingChallenge
_m.ChallengeInfo = ChallengeInfo
_m.FetchResult = FetchResult
_m.FetchStatus = FetchStatus
_m.SessionIdentity = SessionIdentity

_AM = AsyncMock  # anchor reference so import is not pruned
_PY = pytest  # anchor reference so import is not pruned
_UC = _uc.FetchTransactionsUseCase  # anchor
_D = _disp.ProtocolDispatcher  # anchor
_E1 = _exc.BankNotSupportedError  # anchor
_E2 = _exc.SessionNotFoundError  # anchor


def _conn():
    return _m.BankConnection(
        protocol=_m.BankingProtocol.FINTS,
        bank_code="12345678",
        username="testuser",
        pin="secret-pin",
    )


def _fetch():
    return _m.TransactionFetch(
        iban="DE89370400440532013000",
        date_range=_m.DateRange(start=_dt.date(2024, 1, 1), end=_dt.date(2024, 1, 31)),
    )


def _endpoint():
    return _m.BankEndpoint(
        server_url="https://fints.example.com/fints", protocol=_m.BankingProtocol.FINTS
    )


def _identity():
    return _m.SessionIdentity(
        session_id="a" * 32,
        expires_at=_dt.datetime.now(_dt.UTC) + _dt.timedelta(seconds=300),
    )


def _pending(identity=None):
    if identity is None:
        identity = _identity()
    return _m.PendingChallenge(
        identity=identity,
        protocol=_m.BankingProtocol.FINTS,
        bank_code="12345678",
        dialog_state=b"opaque-state",
        challenge_type="photoTAN",
        challenge_text="Enter the code",
        media_data=b"\x89PNG",
    )


def _success_result():
    return _m.FetchResult(
        status=_m.FetchStatus.SUCCESS,
        transactions=[
            _m.TransactionData(
                entry_id="tx1",
                booking_date=_dt.date(2024, 1, 15),
                value_date=_dt.date(2024, 1, 15),
                amount=100,
                currency="EUR",
                purpose="Test payment",
            ),
        ],
    )


def _challenge_result(pending):
    return _m.FetchResult(
        status=_m.FetchStatus.CHALLENGE_REQUIRED,
        challenge=_m.ChallengeInfo(
            session_id=pending.identity.session_id,
            type=pending.challenge_type,
            media_data=pending.media_data,
        ),
        pending_challenge=pending,
    )


@pytest.fixture
def mock_banking_client():
    client = AsyncMock()
    client.fetch_transactions = AsyncMock()
    client.resume_with_tan = AsyncMock()
    return client


@pytest.fixture
def dispatcher(mock_banking_client):
    d = _disp.ProtocolDispatcher()
    d.register(_m.BankingProtocol.FINTS, mock_banking_client)
    return d


@pytest.fixture
def challenge_repo():
    repo = AsyncMock()
    repo.save = AsyncMock()
    repo.get = AsyncMock()
    repo.delete = AsyncMock()
    return repo


@pytest.fixture
def bank_directory():
    repo = AsyncMock()
    repo.resolve = AsyncMock()
    return repo


@pytest.fixture
def use_case(dispatcher, challenge_repo, bank_directory):
    return _uc.FetchTransactionsUseCase(
        dispatcher=dispatcher,
        challenge_repo=challenge_repo,
        bank_directory=bank_directory,
    )


# --- execute_initial tests ---


@pytest.mark.asyncio
async def test_initial_fetch_success(
    use_case,
    mock_banking_client,
    bank_directory,
    challenge_repo,
):
    """Successful initial fetch returns SUCCESS with transactions."""
    endpoint = _endpoint()
    bank_directory.resolve.return_value = endpoint
    mock_banking_client.fetch_transactions.return_value = _success_result()

    connection = _conn()
    fetch = _fetch()
    result = await use_case.execute_initial(connection, fetch)

    assert result.status == _m.FetchStatus.SUCCESS
    assert result.transactions is not None
    assert len(result.transactions) == 1
    bank_directory.resolve.assert_awaited_once_with(
        connection.bank_code,
        connection.protocol,
    )
    mock_banking_client.fetch_transactions.assert_awaited_once_with(
        connection,
        endpoint,
        fetch,
    )
    challenge_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_initial_fetch_challenge_saves_to_repo(
    use_case,
    mock_banking_client,
    bank_directory,
    challenge_repo,
):
    """Initial fetch with CHALLENGE_REQUIRED saves PendingChallenge to repo."""
    endpoint = _endpoint()
    bank_directory.resolve.return_value = endpoint
    pending = _pending()
    mock_banking_client.fetch_transactions.return_value = _challenge_result(pending)

    result = await use_case.execute_initial(_conn(), _fetch())

    assert result.status == _m.FetchStatus.CHALLENGE_REQUIRED
    assert result.challenge is not None
    assert result.challenge.session_id == pending.identity.session_id
    challenge_repo.save.assert_awaited_once_with(pending)


@pytest.mark.asyncio
async def test_initial_fetch_bank_not_supported(use_case, bank_directory):
    """Raises BankNotSupportedError when bank_code cannot be resolved."""
    bank_directory.resolve.return_value = None

    connection = _conn()
    with pytest.raises(_exc.BankNotSupportedError) as exc_info:
        await use_case.execute_initial(connection, _fetch())

    assert exc_info.value.bank_code == connection.bank_code


# --- execute_resume tests ---


@pytest.mark.asyncio
async def test_resume_success(
    use_case, mock_banking_client, challenge_repo, bank_directory
):
    """Successful resume deletes challenge and returns SUCCESS."""
    pending = _pending()
    endpoint = _endpoint()
    challenge_repo.get.return_value = pending
    bank_directory.resolve.return_value = endpoint
    mock_banking_client.resume_with_tan.return_value = _success_result()

    result = await use_case.execute_resume(
        session_id=pending.identity.session_id,
        tan_response="123456",
    )

    assert result.status == _m.FetchStatus.SUCCESS
    assert result.transactions is not None
    mock_banking_client.resume_with_tan.assert_awaited_once_with(
        pending, "123456", endpoint
    )
    challenge_repo.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_resume_session_not_found(use_case, challenge_repo):
    """Raises SessionNotFoundError when challenge not found for session_id."""
    challenge_repo.get.return_value = None

    with pytest.raises(_exc.SessionNotFoundError) as exc_info:
        await use_case.execute_resume(
            session_id="nonexistent-session",
            tan_response="123456",
        )

    assert exc_info.value.session_id == "nonexistent-session"
