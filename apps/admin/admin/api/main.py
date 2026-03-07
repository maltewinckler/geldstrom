"""FastAPI application with lifespan management for the Admin service."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from admin.api import api_keys as api_keys_module
from admin.api import bank_directory as bank_directory_module
from admin.api.api_keys.routes import router as api_keys_router
from admin.api.bank_directory.routes import router as bank_directory_router
from admin.api.error_handlers import register_exception_handlers
from admin.api.webhooks.paypal import router as paypal_router
from admin.application.api_keys.use_cases import (
    CreateAccount,
    CreateApiKey,
    DeleteAccount,
    GetAccount,
    RevokeApiKey,
    RotateApiKey,
)
from admin.application.bank_directory.use_cases import (
    CreateBankEndpoint,
    DeleteBankEndpoint,
    GetBankEndpoint,
    ListBankEndpoints,
    UpdateBankEndpoint,
)
from admin.infrastructure.cache.endpoint_cache import InMemoryEndpointCache
from admin.infrastructure.cache.key_cache import InMemoryKeyCache
from admin.infrastructure.encryption.fernet_encryptor import FernetConfigEncryptor
from admin.infrastructure.grpc.bank_directory_servicer import BankDirectoryServicer
from admin.infrastructure.grpc.key_validation_servicer import KeyValidationServicer
from admin.infrastructure.grpc.server import create_grpc_server
from admin.infrastructure.hashing.argon2_hasher import Argon2idKeyHasher
from admin.infrastructure.persistence.api_keys.repository import (
    AccountRepositoryImpl,
    ApiKeyRepositoryImpl,
)
from admin.infrastructure.persistence.bank_directory.repository import (
    BankEndpointRepositoryImpl,
)

# Global references for cleanup
_engine: AsyncEngine | None = None
_grpc_server = None


def _get_database_url() -> str:
    """Get the database URL from environment variable."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    return database_url


def _get_encryption_key() -> bytes:
    """Get the Fernet encryption key from environment variable."""
    key = os.environ.get("PROTOCOL_CONFIG_ENCRYPTION_KEY")
    if not key:
        raise ValueError(
            "PROTOCOL_CONFIG_ENCRYPTION_KEY environment variable is not set"
        )
    return key.encode()


def _get_grpc_port() -> int:
    """Get the gRPC server port from environment variable."""
    return int(os.environ.get("GRPC_PORT", "50051"))


class SessionScopedApiKeyRepository:
    """API key repository that creates a new session for each operation.

    Used by gRPC servicers which need their own session scope.
    """

    def __init__(
        self, engine: AsyncEngine, config_encryptor: FernetConfigEncryptor
    ) -> None:
        self._engine = engine
        self._config_encryptor = config_encryptor

    async def get_by_sha256_hash(self, sha256_hash):
        """Get an API key by SHA-256 hash with a fresh session."""
        async with AsyncSession(self._engine) as session:
            repo = ApiKeyRepositoryImpl(session)
            return await repo.get_by_sha256_hash(sha256_hash)


class SessionScopedBankEndpointRepository:
    """Bank endpoint repository that creates a new session for each operation.

    Used by gRPC servicers which need their own session scope.
    """

    def __init__(
        self, engine: AsyncEngine, config_encryptor: FernetConfigEncryptor
    ) -> None:
        self._engine = engine
        self._config_encryptor = config_encryptor

    async def get(self, bank_code: str):
        """Get a bank endpoint by bank code with a fresh session."""
        async with AsyncSession(self._engine) as session:
            repo = BankEndpointRepositoryImpl(session, self._config_encryptor)
            return await repo.get(bank_code)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for the FastAPI application.

    Startup:
    1. Create SQLAlchemy async engine
    2. Create Fernet encryptor from PROTOCOL_CONFIG_ENCRYPTION_KEY env var
    3. Create internal caches (InMemoryKeyCache, InMemoryEndpointCache)
    4. Wire all dependencies
    5. Load all active keys and endpoints from PostgreSQL into caches
    6. Start gRPC server on configured port

    Shutdown:
    7. Stop gRPC server gracefully
    8. Close DB engine
    """
    global _engine, _grpc_server

    # 1. Create SQLAlchemy async engine
    database_url = _get_database_url()
    _engine = create_async_engine(database_url, pool_pre_ping=True)

    # 2. Create Fernet encryptor from PROTOCOL_CONFIG_ENCRYPTION_KEY env var
    encryption_key = _get_encryption_key()
    config_encryptor = FernetConfigEncryptor(encryption_key)

    # 3. Create internal caches
    key_cache = InMemoryKeyCache()
    endpoint_cache = InMemoryEndpointCache()

    # 4. Create key hasher
    key_hasher = Argon2idKeyHasher()

    # 5. Load all active keys and endpoints from PostgreSQL into caches
    async with AsyncSession(_engine) as session:
        # Load active API keys into cache
        api_key_repo = ApiKeyRepositoryImpl(session)
        active_keys = await api_key_repo.list_active()
        await key_cache.load_all(
            [(key.sha256_key_hash, key.account_id) for key in active_keys]
        )

        # Load all bank endpoints into cache
        bank_endpoint_repo = BankEndpointRepositoryImpl(session, config_encryptor)
        endpoints = await bank_endpoint_repo.list_all()
        await endpoint_cache.load_all(endpoints)

    # 6. Wire all use cases with dependency injection
    # Create session-scoped repositories for gRPC servicers
    grpc_api_key_repo = SessionScopedApiKeyRepository(_engine, config_encryptor)
    grpc_bank_endpoint_repo = SessionScopedBankEndpointRepository(
        _engine, config_encryptor
    )

    # Create gRPC servicers
    key_validation_servicer = KeyValidationServicer(
        key_cache=key_cache,
        api_key_repo=grpc_api_key_repo,
    )
    bank_directory_servicer = BankDirectoryServicer(
        endpoint_cache=endpoint_cache,
        bank_endpoint_repo=grpc_bank_endpoint_repo,
    )

    # Create and start gRPC server
    grpc_port = _get_grpc_port()
    _grpc_server = await create_grpc_server(
        key_validation_servicer=key_validation_servicer,
        bank_directory_servicer=bank_directory_servicer,
        port=grpc_port,
    )
    await _grpc_server.start()

    # Wire REST API use cases using dependency overrides
    # Create a session factory for request-scoped sessions
    session_factory = async_sessionmaker(_engine, expire_on_commit=False)

    # Override dependency injection functions in routes modules
    # API Keys routes
    def get_create_account() -> CreateAccount:
        session = session_factory()
        return CreateAccount(AccountRepositoryImpl(session))

    def get_get_account() -> GetAccount:
        session = session_factory()
        return GetAccount(
            AccountRepositoryImpl(session),
            ApiKeyRepositoryImpl(session),
        )

    def get_delete_account() -> DeleteAccount:
        session = session_factory()
        return DeleteAccount(AccountRepositoryImpl(session))

    def get_create_api_key() -> CreateApiKey:
        session = session_factory()
        return CreateApiKey(
            AccountRepositoryImpl(session),
            ApiKeyRepositoryImpl(session),
            key_hasher,
            key_cache,
        )

    def get_revoke_api_key() -> RevokeApiKey:
        session = session_factory()
        return RevokeApiKey(
            ApiKeyRepositoryImpl(session),
            key_cache,
        )

    def get_rotate_api_key() -> RotateApiKey:
        session = session_factory()
        return RotateApiKey(
            ApiKeyRepositoryImpl(session),
            key_hasher,
            key_cache,
        )

    # Bank Directory routes
    def get_create_bank_endpoint() -> CreateBankEndpoint:
        session = session_factory()
        return CreateBankEndpoint(
            BankEndpointRepositoryImpl(session, config_encryptor),
            endpoint_cache,
        )

    def get_list_bank_endpoints() -> ListBankEndpoints:
        session = session_factory()
        return ListBankEndpoints(
            BankEndpointRepositoryImpl(session, config_encryptor),
        )

    def get_get_bank_endpoint() -> GetBankEndpoint:
        session = session_factory()
        return GetBankEndpoint(
            BankEndpointRepositoryImpl(session, config_encryptor),
        )

    def get_update_bank_endpoint() -> UpdateBankEndpoint:
        session = session_factory()
        return UpdateBankEndpoint(
            BankEndpointRepositoryImpl(session, config_encryptor),
            endpoint_cache,
        )

    def get_delete_bank_endpoint() -> DeleteBankEndpoint:
        session = session_factory()
        return DeleteBankEndpoint(
            BankEndpointRepositoryImpl(session, config_encryptor),
            endpoint_cache,
        )

    # Override the dependency injection functions in the routes modules
    api_keys_module.routes.get_create_account = get_create_account
    api_keys_module.routes.get_get_account = get_get_account
    api_keys_module.routes.get_delete_account = get_delete_account
    api_keys_module.routes.get_create_api_key = get_create_api_key
    api_keys_module.routes.get_revoke_api_key = get_revoke_api_key
    api_keys_module.routes.get_rotate_api_key = get_rotate_api_key

    bank_directory_module.routes.get_create_bank_endpoint = get_create_bank_endpoint
    bank_directory_module.routes.get_list_bank_endpoints = get_list_bank_endpoints
    bank_directory_module.routes.get_get_bank_endpoint = get_get_bank_endpoint
    bank_directory_module.routes.get_update_bank_endpoint = get_update_bank_endpoint
    bank_directory_module.routes.get_delete_bank_endpoint = get_delete_bank_endpoint

    yield

    # Shutdown
    # 7. Stop gRPC server gracefully
    if _grpc_server is not None:
        await _grpc_server.stop(grace=5)

    # 8. Close DB engine
    if _engine is not None:
        await _engine.dispose()


# Create the FastAPI application with lifespan
app = FastAPI(
    title="Geldstrom Admin Service",
    description="Control Plane for API key lifecycle and bank directory management",
    version="1.0.0",
    lifespan=lifespan,
)

# Register exception handlers
register_exception_handlers(app)

# Register routers with correct prefixes
# api_keys router already has /admin prefix
app.include_router(api_keys_router)
# bank_directory router already has /admin/bank-endpoints prefix
app.include_router(bank_directory_router)
# Include webhooks router
app.include_router(paypal_router)


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}
