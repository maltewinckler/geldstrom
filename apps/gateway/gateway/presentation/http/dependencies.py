"""FastAPI dependencies for authentication and consumer resolution."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from gateway.application.ports import ApplicationFactory
from gateway.config import Settings
from gateway.infrastructure.gateway_factory import GatewayApplicationFactory


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and cache the gateway runtime settings."""
    return Settings()


@lru_cache(maxsize=1)
def get_factory() -> GatewayApplicationFactory:
    """Build and cache the application factory singleton."""
    return GatewayApplicationFactory(get_settings())


_bearer = HTTPBearer(auto_error=False)


async def get_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """Extract the raw API key from the ``Authorization: Bearer …`` header."""
    if credentials is None or not credentials.credentials:
        from fastapi import HTTPException

        from .schemas.errors import ErrorResponse

        raise HTTPException(
            status_code=401,
            detail=ErrorResponse(
                error="unauthorized", message="Missing API key"
            ).model_dump(),
        )
    return credentials.credentials


ApiKey = Annotated[str, Depends(get_api_key)]
Factory = Annotated[ApplicationFactory, Depends(get_factory)]
