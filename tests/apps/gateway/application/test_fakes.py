"""Smoke tests for reusable application-layer fakes."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from pydantic import SecretStr

from gateway.application.common import InternalError
from gateway.domain.banking_gateway import (
    AccountsResult,
    OperationStatus,
    PendingOperationSession,
    PresentedBankCredentials,
    PresentedBankPassword,
    PresentedBankUserId,
    ResumeResult,
)
from gateway.domain.consumer_access import (
    ApiConsumer,
    ApiKeyHash,
    ConsumerId,
    ConsumerStatus,
    EmailAddress,
)
from gateway.domain.institution_catalog import (
    BankLeitzahl,
    Bic,
    FinTSInstitute,
    InstituteEndpoint,
)
from gateway.domain.shared import BankProtocol
from tests.apps.gateway.fakes import (
    FakeBankingConnector,
    FakeConsumerCache,
    FakeIdProvider,
    FakeInstituteCache,
    FakeOperationSessionStore,
    FakeProductKeyProvider,
)


def test_fake_consumer_cache_returns_loaded_consumers() -> None:
    consumer = ApiConsumer(
        consumer_id=ConsumerId.from_string("12345678-1234-5678-1234-567812345678"),
        email=EmailAddress("consumer@example.com"),
        api_key_hash=ApiKeyHash("hash-1"),
        status=ConsumerStatus.ACTIVE,
        created_at=datetime(2026, 3, 7, tzinfo=UTC),
    )
    cache = FakeConsumerCache([consumer])

    loaded = _run(cache.list_active())

    assert loaded == [consumer]


def test_fake_institute_cache_indexes_by_blz() -> None:
    institute = FinTSInstitute(
        blz=BankLeitzahl("12345678"),
        bic=Bic("GENODEF1ABC"),
        name="Example Bank",
        city="Berlin",
        organization="Example Org",
        pin_tan_url=InstituteEndpoint("https://bank.example/fints"),
        fints_version="3.0",
        last_source_update=date(2026, 3, 7),
        source_row_checksum="checksum-1",
        source_payload={"row": 1},
    )
    cache = FakeInstituteCache([institute])

    loaded = _run(cache.get_by_blz(BankLeitzahl("12345678")))

    assert loaded == institute


def test_fake_product_key_provider_raises_when_unset() -> None:
    provider = FakeProductKeyProvider()

    try:
        _run(provider.require_current())
    except InternalError as error:
        assert error.code.value == "internal_error"
    else:
        raise AssertionError("Expected InternalError when no product key is loaded")


def test_fake_operation_session_store_can_expire_stale_sessions() -> None:
    now = datetime(2026, 3, 7, 12, 0, tzinfo=UTC)
    session = PendingOperationSession(
        operation_id="op-1",
        consumer_id=ConsumerId.from_string("12345678-1234-5678-1234-567812345678"),
        protocol=BankProtocol.FINTS,
        operation_type="accounts",
        session_state=b"state",
        status=OperationStatus.PENDING_CONFIRMATION,
        created_at=now - timedelta(minutes=5),
        expires_at=now - timedelta(minutes=1),
    )
    store = FakeOperationSessionStore([session])

    expired_count = _run(store.expire_stale(now))

    assert expired_count == 1
    assert _run(store.get("op-1")) is None


def test_fake_banking_connector_returns_queued_results_and_records_calls() -> None:
    connector = FakeBankingConnector(
        accounts_results=[
            AccountsResult(
                status=OperationStatus.COMPLETED,
                accounts=[{"account_id": "acc-1"}],
            )
        ],
        resume_results=[
            ResumeResult(
                status=OperationStatus.COMPLETED,
                result_payload={"accounts": []},
            )
        ],
    )
    credentials = PresentedBankCredentials(
        user_id=PresentedBankUserId(SecretStr("user-1")),
        password=PresentedBankPassword(SecretStr("pass-1")),
    )
    institute = FinTSInstitute(
        blz=BankLeitzahl("12345678"),
        bic=Bic("GENODEF1ABC"),
        name="Example Bank",
        city="Berlin",
        organization="Example Org",
        pin_tan_url=InstituteEndpoint("https://bank.example/fints"),
        fints_version="3.0",
        last_source_update=date(2026, 3, 7),
        source_row_checksum="checksum-1",
        source_payload={"row": 1},
    )

    accounts_result = _run(connector.list_accounts(institute, credentials))
    resume_result = _run(connector.resume_operation(b"opaque-state"))

    assert accounts_result.accounts == [{"account_id": "acc-1"}]
    assert resume_result.result_payload == {"accounts": []}
    assert [call[0] for call in connector.calls] == [
        "list_accounts",
        "resume_operation",
    ]


def test_fake_id_provider_is_deterministic_and_advances_time() -> None:
    provider = FakeIdProvider(
        now_value=datetime(2026, 3, 7, 12, 0, tzinfo=UTC),
        operation_ids=["op-1", "op-2"],
    )

    assert provider.new_operation_id() == "op-1"
    provider.advance(minutes=5)
    assert provider.now() == datetime(2026, 3, 7, 12, 5, tzinfo=UTC)
    assert provider.new_operation_id() == "op-2"


def _run(awaitable):
    import asyncio

    return asyncio.run(awaitable)
