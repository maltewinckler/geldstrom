"""Tests for gateway administration use cases."""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

from gateway.application.administration.commands import (
    CreateApiConsumerCommand,
    DeleteApiConsumerCommand,
    DisableApiConsumerCommand,
    RotateApiConsumerKeyCommand,
    SyncInstituteCatalogCommand,
    UpdateApiConsumerCommand,
    UpdateProductRegistrationCommand,
)
from gateway.application.administration.queries import (
    InspectBackendStateQuery,
    ListApiConsumersQuery,
)
from gateway.application.health.queries.evaluate_health import EvaluateHealthQuery
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
from gateway.domain.product_registration import FinTSProductRegistration
from tests.apps.gateway.fakes import (
    FakeIdProvider,
    FakeInstituteCache,
    FakeProductKeyProvider,
)


class FakeApiKeyService:
    def __init__(self, generated_keys: list[str] | None = None) -> None:
        self._generated_keys = list(generated_keys or ["raw-key-1"])

    def generate(self) -> str:
        return self._generated_keys.pop(0)

    def hash(self, raw_key: str) -> ApiKeyHash:
        return ApiKeyHash(f"hashed::{raw_key}")


class FakeConsumerRepository:
    def __init__(self, consumers: list[ApiConsumer] | None = None) -> None:
        self._consumers = {str(consumer.consumer_id): consumer for consumer in consumers or []}

    async def list_all(self) -> list[ApiConsumer]:
        return sorted(self._consumers.values(), key=lambda consumer: consumer.email.value)

    async def get_by_id(self, consumer_id: ConsumerId) -> ApiConsumer | None:
        return self._consumers.get(str(consumer_id))

    async def get_by_email(self, email: EmailAddress) -> ApiConsumer | None:
        for consumer in self._consumers.values():
            if consumer.email == email:
                return consumer
        return None

    async def list_all_active(self) -> list[ApiConsumer]:
        return [
            consumer
            for consumer in await self.list_all()
            if consumer.status is ConsumerStatus.ACTIVE
        ]

    async def save(self, consumer: ApiConsumer) -> None:
        self._consumers[str(consumer.consumer_id)] = consumer


class FakeConsumerCacheWriter:
    def __init__(self) -> None:
        self._active: dict[str, ApiConsumer] = {}

    async def reload_one(self, consumer: ApiConsumer) -> None:
        if consumer.status is ConsumerStatus.ACTIVE:
            self._active[str(consumer.consumer_id)] = consumer
        else:
            self._active.pop(str(consumer.consumer_id), None)

    async def list_active(self) -> list[ApiConsumer]:
        return list(self._active.values())


class FakeInstituteReader:
    def __init__(self, institutes: list[FinTSInstitute]) -> None:
        self._institutes = institutes
        self.last_path: Path | None = None

    def read(self, path: Path) -> list[FinTSInstitute]:
        self.last_path = path
        return list(self._institutes)


class FakeInstituteRepository:
    def __init__(self, institutes: list[FinTSInstitute] | None = None) -> None:
        self._institutes = {institute.blz.value: institute for institute in institutes or []}

    async def get_by_blz(self, blz: BankLeitzahl) -> FinTSInstitute | None:
        return self._institutes.get(blz.value)

    async def list_all(self) -> list[FinTSInstitute]:
        return [self._institutes[key] for key in sorted(self._institutes)]

    async def replace_catalog(self, institutes: list[FinTSInstitute]) -> None:
        self._institutes = {institute.blz.value: institute for institute in institutes}


class FakeProductRegistrationRepository:
    def __init__(self, current: FinTSProductRegistration | None = None) -> None:
        self._current = current

    async def get_current(self) -> FinTSProductRegistration | None:
        return self._current

    async def save_current(self, registration: FinTSProductRegistration) -> None:
        self._current = registration


class FakeProductRegistrationCache:
    def __init__(self) -> None:
        self.current: FinTSProductRegistration | None = None

    async def set_current(self, registration: FinTSProductRegistration | None) -> None:
        self.current = registration


class HealthyCheck:
    def __init__(self, healthy: bool) -> None:
        self._healthy = healthy

    async def __call__(self) -> bool:
        return self._healthy


def test_create_api_consumer_returns_raw_key_once() -> None:
    repository = FakeConsumerRepository()
    cache = FakeConsumerCacheWriter()
    use_case = CreateApiConsumerCommand(
        repository=repository,
        consumer_cache=cache,
        api_key_service=FakeApiKeyService(["raw-key-1"]),
        id_provider=FakeIdProvider(
            now_value=datetime(2026, 3, 12, 10, 0, tzinfo=UTC),
            operation_ids=["12345678-1234-5678-1234-567812345678"],
        ),
    )

    result = asyncio.run(use_case("consumer@example.com"))
    stored = asyncio.run(repository.get_by_email(EmailAddress("consumer@example.com")))
    active = asyncio.run(cache.list_active())

    assert result.raw_api_key == "raw-key-1"
    assert result.consumer.email == "consumer@example.com"
    assert stored is not None
    assert stored.api_key_hash == ApiKeyHash("hashed::raw-key-1")
    assert active == [stored]


def test_list_api_consumers_returns_summaries_without_secret_fields() -> None:
    repository = FakeConsumerRepository(
        [
            _consumer(),
            _consumer(
                consumer_id="87654321-4321-8765-4321-876543218765",
                email="b@example.com",
            ),
        ]
    )

    result = asyncio.run(ListApiConsumersQuery(repository)())

    assert [summary.email for summary in result] == ["b@example.com", "consumer@example.com"]
    assert all(not hasattr(summary, "api_key_hash") for summary in result)


def test_update_api_consumer_changes_email() -> None:
    consumer = _consumer()
    repository = FakeConsumerRepository([consumer])
    cache = FakeConsumerCacheWriter()
    asyncio.run(cache.reload_one(consumer))
    use_case = UpdateApiConsumerCommand(repository=repository, consumer_cache=cache)

    result = asyncio.run(
        use_case(str(consumer.consumer_id), email="updated@example.com")
    )
    stored = asyncio.run(repository.get_by_id(consumer.consumer_id))

    assert result.email == "updated@example.com"
    assert stored is not None
    assert stored.email == EmailAddress("updated@example.com")


def test_rotate_api_consumer_key_returns_new_raw_key_once() -> None:
    consumer = _consumer(status=ConsumerStatus.ACTIVE)
    repository = FakeConsumerRepository([consumer])
    cache = FakeConsumerCacheWriter()
    asyncio.run(cache.reload_one(consumer))
    use_case = RotateApiConsumerKeyCommand(
        repository=repository,
        consumer_cache=cache,
        api_key_service=FakeApiKeyService(["raw-key-2"]),
        id_provider=FakeIdProvider(
            now_value=datetime(2026, 3, 12, 11, 0, tzinfo=UTC),
            operation_ids=["unused"],
        ),
    )

    result = asyncio.run(use_case(str(consumer.consumer_id)))
    stored = asyncio.run(repository.get_by_id(consumer.consumer_id))

    assert result.raw_api_key == "raw-key-2"
    assert stored is not None
    assert stored.api_key_hash == ApiKeyHash("hashed::raw-key-2")
    assert stored.rotated_at == datetime(2026, 3, 12, 11, 0, tzinfo=UTC)


def test_disable_and_delete_api_consumer_refresh_cache_and_clear_hash() -> None:
    consumer = _consumer()
    repository = FakeConsumerRepository([consumer])
    cache = FakeConsumerCacheWriter()
    asyncio.run(cache.reload_one(consumer))

    disabled = asyncio.run(
        DisableApiConsumerCommand(repository=repository, consumer_cache=cache)(
            str(consumer.consumer_id)
        )
    )
    deleted = asyncio.run(
        DeleteApiConsumerCommand(repository=repository, consumer_cache=cache)(
            str(consumer.consumer_id)
        )
    )
    stored = asyncio.run(repository.get_by_id(consumer.consumer_id))

    assert disabled.status is ConsumerStatus.DISABLED
    assert deleted.status is ConsumerStatus.DELETED
    assert stored is not None
    assert stored.api_key_hash is None
    assert asyncio.run(cache.list_active()) == []


def test_sync_institute_catalog_canonicalizes_and_refreshes_cache() -> None:
    newer = _institute(name="Preferred", last_source_update=date(2026, 3, 10))
    older = _institute(name="Older", last_source_update=date(2026, 3, 1))
    reader = FakeInstituteReader([older, newer])
    repository = FakeInstituteRepository()
    cache = FakeInstituteCache()
    use_case = SyncInstituteCatalogCommand(reader, repository, cache)

    result = asyncio.run(use_case(Path("institutes.csv")))
    stored = asyncio.run(repository.get_by_blz(BankLeitzahl("12345678")))
    cached = asyncio.run(cache.get_by_blz(BankLeitzahl("12345678")))

    assert result.loaded_count == 1
    assert reader.last_path == Path("institutes.csv")
    assert stored is not None
    assert stored.name == "Preferred"
    assert cached == stored


def test_update_product_registration_refreshes_cache_and_current_key_provider() -> None:
    repository = FakeProductRegistrationRepository()
    cache = FakeProductRegistrationCache()
    current_key_provider = FakeProductKeyProvider()
    use_case = UpdateProductRegistrationCommand(
        repository=repository,
        product_registration_cache=cache,
        current_product_key_provider=current_key_provider,
        product_key_service=_FakeProductKeyService(),
        id_provider=FakeIdProvider(
            now_value=datetime(2026, 3, 12, 12, 0, tzinfo=UTC),
            operation_ids=["87654321-4321-8765-4321-876543218765"],
        ),
        product_version="1.0.0",
        key_version="v1",
    )

    result = asyncio.run(use_case("new-product-key"))
    stored = asyncio.run(repository.get_current())
    current_key = asyncio.run(current_key_provider.require_current())

    assert result.product_version == "1.0.0"
    assert stored is not None
    assert cache.current == stored
    assert current_key == "new-product-key"


def test_inspect_backend_state_returns_sanitized_snapshot() -> None:
    consumer = _consumer()
    disabled_consumer = _consumer(
        consumer_id="87654321-4321-8765-4321-876543218765",
        email="disabled@example.com",
        status=ConsumerStatus.DISABLED,
        api_key_hash=ApiKeyHash("hash-2"),
    )
    registration = _registration()
    use_case = InspectBackendStateQuery(
        evaluate_health=EvaluateHealthQuery(
            {
                "postgres": HealthyCheck(True),
                "consumer_cache": HealthyCheck(True),
            }
        ),
        consumer_repository=FakeConsumerRepository([consumer, disabled_consumer]),
        institute_repository=FakeInstituteRepository([_institute()]),
        product_registration_repository=FakeProductRegistrationRepository(registration),
    )

    result = asyncio.run(use_case(blz=BankLeitzahl("12345678")))

    assert result.health["status"] == "ready"
    assert result.total_consumer_count == 2
    assert result.active_consumer_count == 1
    assert result.institute_count == 1
    assert result.selected_institute is not None
    assert result.product_registration is not None
    assert result.product_registration.product_version == "1.0.0"


class _FakeProductKeyService:
    def encrypt(self, plaintext: str):
        from gateway.domain.product_registration import EncryptedProductKey

        return EncryptedProductKey(bytes(f"encrypted::{plaintext}", "utf-8"))


def _consumer(
    *,
    consumer_id: str = "12345678-1234-5678-1234-567812345678",
    email: str = "consumer@example.com",
    status: ConsumerStatus = ConsumerStatus.ACTIVE,
    api_key_hash: ApiKeyHash | None = None,
) -> ApiConsumer:
    return ApiConsumer(
        consumer_id=ConsumerId(UUID(consumer_id)),
        email=EmailAddress(email),
        api_key_hash=api_key_hash or ApiKeyHash("hash-1"),
        status=status,
        created_at=datetime(2026, 3, 12, 9, 0, tzinfo=UTC),
    )


def _institute(
    *,
    name: str = "Example Bank",
    last_source_update: date | None = None,
) -> FinTSInstitute:
    return FinTSInstitute(
        blz=BankLeitzahl("12345678"),
        bic=Bic("GENODEF1ABC"),
        name=name,
        city="Berlin",
        organization="Example Org",
        pin_tan_url=InstituteEndpoint("https://bank.example/fints"),
        fints_version="3.0",
        last_source_update=last_source_update or date(2026, 3, 7),
        source_row_checksum=f"checksum::{name}",
        source_payload={"name": name},
    )


def _registration() -> FinTSProductRegistration:
    from gateway.domain.product_registration import (
        EncryptedProductKey,
        KeyVersion,
        ProductVersion,
    )
    from gateway.domain.shared import EntityId

    return FinTSProductRegistration(
        registration_id=EntityId(UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")),
        encrypted_product_key=EncryptedProductKey(b"encrypted::current"),
        product_version=ProductVersion("1.0.0"),
        key_version=KeyVersion("v1"),
        updated_at=datetime(2026, 3, 12, 8, 0, tzinfo=UTC),
    )
