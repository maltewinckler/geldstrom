"""Tests for admin CLI use cases."""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

from gateway_admin_cli.application.commands import (
    CreateUserCommand,
    DeleteUserCommand,
    DisableUserCommand,
    RotateUserKeyCommand,
    SyncInstituteCatalogCommand,
    UpdateProductRegistrationCommand,
    UpdateUserCommand,
)
from gateway_admin_cli.application.queries import (
    InspectBackendStateQuery,
    ListUsersQuery,
)
from gateway_admin_cli.domain.institutes import (
    BankLeitzahl,
    Bic,
    FinTSInstitute,
    InstituteEndpoint,
)
from gateway_admin_cli.domain.product import ProductRegistration
from gateway_admin_cli.domain.users import ApiKeyHash, Email, User, UserId, UserStatus


class FakeApiKeyService:
    def __init__(self, generated_keys: list[str] | None = None) -> None:
        self._generated_keys = list(generated_keys or ["raw-key-1"])

    def generate(self, consumer_id: str) -> str:
        return self._generated_keys.pop(0)

    def hash(self, raw_key: str) -> ApiKeyHash:
        return ApiKeyHash(f"hashed::{raw_key}")


class FakeUserRepository:
    def __init__(self, users: list[User] | None = None) -> None:
        self._users = {str(user.user_id): user for user in users or []}

    async def list_all(self) -> list[User]:
        return sorted(self._users.values(), key=lambda user: user.email.value)

    async def get_by_id(self, user_id: UserId) -> User | None:
        return self._users.get(str(user_id))

    async def get_by_email(self, email: Email) -> User | None:
        for user in self._users.values():
            if user.email == email:
                return user
        return None

    async def save(self, user: User) -> None:
        self._users[str(user.user_id)] = user


class FakeUserCacheWriter:
    def __init__(self) -> None:
        self._active: dict[str, User] = {}

    async def reload_one(self, user: User) -> None:
        if user.status is UserStatus.ACTIVE:
            self._active[str(user.user_id)] = user
        else:
            self._active.pop(str(user.user_id), None)

    async def list_active(self) -> list[User]:
        return list(self._active.values())


class FakeInstituteReader:
    def __init__(self, institutes: list[FinTSInstitute]) -> None:
        self._institutes = institutes
        self.last_path: Path | None = None

    def read(self, path: Path) -> tuple[list[FinTSInstitute], list]:
        self.last_path = path
        return list(self._institutes), []


class FakeInstituteRepository:
    def __init__(self, institutes: list[FinTSInstitute] | None = None) -> None:
        self._institutes = {
            institute.blz.value: institute for institute in institutes or []
        }

    async def get_by_blz(self, blz: BankLeitzahl) -> FinTSInstitute | None:
        return self._institutes.get(blz.value)

    async def list_all(self) -> list[FinTSInstitute]:
        return [self._institutes[key] for key in sorted(self._institutes)]

    async def replace_catalog(self, institutes: list[FinTSInstitute]) -> None:
        self._institutes = {institute.blz.value: institute for institute in institutes}


class FakeInstituteCache:
    def __init__(self) -> None:
        self._institutes: dict[str, FinTSInstitute] = {}

    async def load(self, institutes: list[FinTSInstitute]) -> None:
        self._institutes = {institute.blz.value: institute for institute in institutes}

    async def get_by_blz(self, blz: BankLeitzahl) -> FinTSInstitute | None:
        return self._institutes.get(blz.value)


class FakeProductRegistrationRepository:
    def __init__(self, current: ProductRegistration | None = None) -> None:
        self._current = current

    async def get_current(self) -> ProductRegistration | None:
        return self._current

    async def save_current(self, registration: ProductRegistration) -> None:
        self._current = registration


class FakeProductRegistrationNotifier:
    def __init__(self) -> None:
        self.notified_count = 0

    async def set_current(self, registration: ProductRegistration | None) -> None:
        self.notified_count += 1


class FakeIdProvider:
    def __init__(
        self,
        now_value: datetime,
        operation_ids: list[str],
    ) -> None:
        self._now_value = now_value
        self._operation_ids = list(operation_ids)

    def new_operation_id(self) -> str:
        return self._operation_ids.pop(0)

    def now(self) -> datetime:
        return self._now_value


def test_create_user_returns_raw_key_once() -> None:
    repository = FakeUserRepository()
    cache = FakeUserCacheWriter()
    use_case = CreateUserCommand(
        repository=repository,
        user_cache_writer=cache,
        api_key_service=FakeApiKeyService(["raw-key-1"]),
        id_provider=FakeIdProvider(
            now_value=datetime(2026, 3, 12, 10, 0, tzinfo=UTC),
            operation_ids=["12345678-1234-5678-1234-567812345678"],
        ),
    )

    result = asyncio.run(use_case("consumer@example.com"))
    stored = asyncio.run(repository.get_by_email(Email("consumer@example.com")))
    active = asyncio.run(cache.list_active())

    assert result.raw_api_key == "raw-key-1"
    assert result.user.email == "consumer@example.com"
    assert stored is not None
    assert stored.api_key_hash == ApiKeyHash("hashed::raw-key-1")
    assert active == [stored]


def test_list_users_returns_summaries_without_secret_fields() -> None:
    repository = FakeUserRepository(
        [
            _user(),
            _user(
                user_id="87654321-4321-8765-4321-876543218765",
                email="b@example.com",
            ),
        ]
    )

    result = asyncio.run(ListUsersQuery(repository)())

    assert [summary.email for summary in result] == [
        "b@example.com",
        "consumer@example.com",
    ]
    assert all(not hasattr(summary, "api_key_hash") for summary in result)


def test_update_user_changes_email() -> None:
    user = _user()
    repository = FakeUserRepository([user])
    cache = FakeUserCacheWriter()
    asyncio.run(cache.reload_one(user))
    use_case = UpdateUserCommand(repository=repository, user_cache_writer=cache)

    result = asyncio.run(use_case(str(user.user_id), email="updated@example.com"))
    stored = asyncio.run(repository.get_by_id(user.user_id))

    assert result.email == "updated@example.com"
    assert stored is not None
    assert stored.email == Email("updated@example.com")


def test_rotate_user_key_returns_new_raw_key_once() -> None:
    user = _user(status=UserStatus.ACTIVE)
    repository = FakeUserRepository([user])
    cache = FakeUserCacheWriter()
    asyncio.run(cache.reload_one(user))
    use_case = RotateUserKeyCommand(
        repository=repository,
        user_cache_writer=cache,
        api_key_service=FakeApiKeyService(["raw-key-2"]),
        id_provider=FakeIdProvider(
            now_value=datetime(2026, 3, 12, 11, 0, tzinfo=UTC),
            operation_ids=["unused"],
        ),
    )

    result = asyncio.run(use_case(str(user.user_id)))
    stored = asyncio.run(repository.get_by_id(user.user_id))

    assert result.raw_api_key == "raw-key-2"
    assert stored is not None
    assert stored.api_key_hash == ApiKeyHash("hashed::raw-key-2")
    assert stored.rotated_at == datetime(2026, 3, 12, 11, 0, tzinfo=UTC)


def test_disable_and_delete_user_refresh_cache_and_clear_hash() -> None:
    user = _user()
    repository = FakeUserRepository([user])
    cache = FakeUserCacheWriter()
    asyncio.run(cache.reload_one(user))

    disabled = asyncio.run(
        DisableUserCommand(repository=repository, user_cache_writer=cache)(
            str(user.user_id)
        )
    )
    deleted = asyncio.run(
        DeleteUserCommand(repository=repository, user_cache_writer=cache)(
            str(user.user_id)
        )
    )
    stored = asyncio.run(repository.get_by_id(user.user_id))

    assert disabled.status is UserStatus.DISABLED
    assert deleted.status is UserStatus.DELETED
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


def test_update_product_registration_saves_and_notifies() -> None:
    repository = FakeProductRegistrationRepository()
    notifier = FakeProductRegistrationNotifier()
    use_case = UpdateProductRegistrationCommand(
        repository=repository,
        product_registration_notifier=notifier,
        id_provider=FakeIdProvider(
            now_value=datetime(2026, 3, 12, 12, 0, tzinfo=UTC),
            operation_ids=[],
        ),
        product_version="1.0.0",
    )

    result = asyncio.run(use_case("new-product-key"))
    stored = asyncio.run(repository.get_current())

    assert result.product_version == "1.0.0"
    assert stored is not None
    assert stored.product_key == "new-product-key"
    assert notifier.notified_count == 1


def test_inspect_backend_state_returns_sanitized_snapshot() -> None:
    user = _user()
    disabled_user = _user(
        user_id="87654321-4321-8765-4321-876543218765",
        email="disabled@example.com",
        status=UserStatus.DISABLED,
        api_key_hash=ApiKeyHash("hash-2"),
    )
    registration = _registration()
    use_case = InspectBackendStateQuery(
        user_repository=FakeUserRepository([user, disabled_user]),
        institute_repository=FakeInstituteRepository([_institute()]),
        product_registration_repository=FakeProductRegistrationRepository(registration),
    )

    result = asyncio.run(use_case(blz="12345678"))

    assert result.db_connectivity == "ok"
    assert result.total_user_count == 2
    assert result.active_user_count == 1
    assert result.institute_count == 1
    assert result.selected_institute is not None
    assert result.product_registration is not None
    assert result.product_registration.product_version == "1.0.0"


def _user(
    *,
    user_id: str = "12345678-1234-5678-1234-567812345678",
    email: str = "consumer@example.com",
    status: UserStatus = UserStatus.ACTIVE,
    api_key_hash: ApiKeyHash | None = None,
) -> User:
    return User(
        user_id=UserId(UUID(user_id)),
        email=Email(email),
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


def _registration() -> ProductRegistration:
    return ProductRegistration(
        product_key="current-product-key",
        product_version="1.0.0",
        updated_at=datetime(2026, 3, 12, 8, 0, tzinfo=UTC),
    )
