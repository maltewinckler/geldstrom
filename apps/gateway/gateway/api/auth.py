"""FastAPI dependency for API key authentication.

Extracts the X-API-Key header, validates it via the ApiKeyValidator port,
and injects the account_id into request state for downstream handlers.

HTTP status mapping:
  - 401: Missing X-API-Key header
  - 403: Invalid API key
  - 503: Validator backend unavailable
"""

from __future__ import annotations

from fastapi import HTTPException, Request

from gateway.domain.session.ports.services import ApiKeyValidator
from gateway.infrastructure.session.api_key_validator import ApiKeyValidationError

# Paths that bypass authentication entirely.
_PUBLIC_PATHS: set[str] = {"/health", "/v1/system/version"}


def create_auth_dependency(validator: ApiKeyValidator):
    """Create a FastAPI dependency that authenticates requests via API key.

    Returns a dependency function suitable for use with ``Depends()``.
    The validator instance is captured via closure so it can be wired
    at application startup.
    """

    async def require_api_key(request: Request) -> str:
        """Validate the X-API-Key header and return the account_id.

        Skips validation for public paths (/health, /v1/system/version).
        Sets ``request.state.account_id`` for downstream handlers.
        """
        if request.url.path in _PUBLIC_PATHS:
            return ""

        api_key = request.headers.get("x-api-key")
        if not api_key:
            raise HTTPException(status_code=401, detail="Missing X-API-Key header")

        try:
            result = await validator.validate(api_key)
        except ApiKeyValidationError:
            raise HTTPException(
                status_code=503,
                detail="API key validation service unavailable",
            )

        if not result.is_valid:
            raise HTTPException(status_code=403, detail="Invalid API key")

        request.state.account_id = result.account_id
        return result.account_id  # type: ignore[return-value]

    return require_api_key
