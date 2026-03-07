"""FastAPI application assembly and dependency injection.

Wires all infrastructure adapters, domain services, and API layer components
at startup using FastAPI's lifespan context manager. Shuts down cleanly on
application exit.

Environment variables:
  REDIS_URL              — Redis connection URL (default: redis://localhost:6379)
  CHALLENGE_ENCRYPTION_KEY — Fernet key for encrypting parked challenge state
  ADMIN_GRPC_URL         — Admin gRPC service URL (default: localhost:50051)
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import grpc.aio
import redis.asyncio as aioredis
from fastapi import FastAPI

from gateway.api.auth import create_auth_dependency
from gateway.api.middleware import LogScrubberMiddleware
from gateway.api.routes import create_router
from gateway.application.use_cases import FetchTransactionsUseCase
from gateway.domain.banking.value_objects.connection import BankingProtocol
from gateway.domain.dispatch import ProtocolDispatcher
from gateway.infrastructure.banking.directory import GrpcBankDirectoryRepository
from gateway.infrastructure.banking.fints.client import FinTSBankingClient
from gateway.infrastructure.session.api_key_validator import GrpcApiKeyValidator
from gateway.infrastructure.session.audit_publisher import LogAuditEventPublisher
from gateway.infrastructure.session.challenge_repo import RedisChallengeRepository

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup: create adapters, wire dependencies. Shutdown: release resources."""

    # --- Redis connection (for challenge state only) ---
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    redis_conn = aioredis.from_url(redis_url, decode_responses=False)

    # --- Admin gRPC channel ---
    admin_grpc_url = os.environ.get("ADMIN_GRPC_URL", "localhost:50051")
    grpc_channel = grpc.aio.insecure_channel(admin_grpc_url)

    # --- Infrastructure adapters ---
    fints_client = FinTSBankingClient()

    encryption_key = os.environ.get("CHALLENGE_ENCRYPTION_KEY", "").encode()
    challenge_repo = RedisChallengeRepository(
        redis=redis_conn, encryption_key=encryption_key
    )

    # API key validator using Admin gRPC ValidateKey
    api_key_validator = GrpcApiKeyValidator(channel=grpc_channel)

    # Bank directory using Admin gRPC GetBankEndpoint
    bank_directory = GrpcBankDirectoryRepository(channel=grpc_channel)

    audit_publisher = LogAuditEventPublisher()

    # --- Domain dispatch ---
    dispatcher = ProtocolDispatcher()
    dispatcher.register(BankingProtocol.FINTS, fints_client)

    # --- Application use case ---
    use_case = FetchTransactionsUseCase(
        dispatcher=dispatcher,
        challenge_repo=challenge_repo,
        bank_directory=bank_directory,
    )

    # --- Auth dependency ---
    require_api_key = create_auth_dependency(api_key_validator)

    # --- Routes ---
    router = create_router(
        use_case=use_case,
        audit_publisher=audit_publisher,
        require_api_key=require_api_key,
    )
    app.include_router(router)

    logger.info("Gateway started (Admin gRPC: %s)", admin_grpc_url)

    yield

    # --- Shutdown ---
    await grpc_channel.close()
    await redis_conn.aclose()
    logger.info("Gateway shut down")


app = FastAPI(lifespan=lifespan)

# Register ASGI middleware (outermost layer — runs before routing).
app.add_middleware(LogScrubberMiddleware)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
