"""FastAPI dependencies for authentication and consumer resolution."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from gateway.application.auth.queries.authenticate_consumer import (
    AuthenticateConsumerQuery,
)
from gateway.application.common import ForbiddenError, UnauthorizedError
from gateway.application.ports import ApplicationFactory
from gateway.config import Settings
from gateway.domain.banking_gateway import AuthenticatedConsumer
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


def get_factory_dep() -> ApplicationFactory:
    return get_factory()


ApiKey = Annotated[str, Depends(get_api_key)]
Factory = Annotated[ApplicationFactory, Depends(get_factory_dep)]


async def get_authenticated_consumer(
    api_key: ApiKey,
    factory: Factory,
) -> AuthenticatedConsumer:
    """Authenticate the consumer and return the identity.

    Raises HTTP 401 for missing/invalid keys and HTTP 403 for disabled consumers.
    """
    from fastapi import HTTPException

    from .schemas.errors import ErrorResponse

    try:
        return await AuthenticateConsumerQuery.from_factory(factory)(api_key)
    except UnauthorizedError as exc:
        raise HTTPException(
            status_code=401,
            detail=ErrorResponse(
                error="unauthorized", message=exc.message
            ).model_dump(),
        ) from exc
    except ForbiddenError as exc:
        raise HTTPException(
            status_code=403,
            detail=ErrorResponse(error="forbidden", message=exc.message).model_dump(),
        ) from exc


AuthConsumer = Annotated[AuthenticatedConsumer, Depends(get_authenticated_consumer)]
