"""FastAPI exception handlers for domain exceptions."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from admin.domain.exceptions import (
    AccountHasKeysError,
    AccountNotFoundError,
    ApiKeyAlreadyExistsError,
    ApiKeyAlreadyRevokedError,
    ApiKeyNotFoundError,
    BankEndpointAlreadyExistsError,
    BankEndpointNotFoundError,
)


class ErrorResponse(BaseModel):
    """Standard error response body."""

    error: str  # machine-readable code
    detail: str  # human-readable message


def _create_error_response(status_code: int, error: str, detail: str) -> JSONResponse:
    """Create a JSON error response."""
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(error=error, detail=detail).model_dump(),
    )


async def account_not_found_handler(
    request: Request, exc: AccountNotFoundError
) -> JSONResponse:
    """Handle AccountNotFoundError -> 404."""
    return _create_error_response(
        status_code=404,
        error="account_not_found",
        detail=str(exc),
    )


async def account_has_keys_handler(
    request: Request, exc: AccountHasKeysError
) -> JSONResponse:
    """Handle AccountHasKeysError -> 409."""
    return _create_error_response(
        status_code=409,
        error="account_has_keys",
        detail=str(exc),
    )


async def api_key_not_found_handler(
    request: Request, exc: ApiKeyNotFoundError
) -> JSONResponse:
    """Handle ApiKeyNotFoundError -> 404."""
    return _create_error_response(
        status_code=404,
        error="api_key_not_found",
        detail=str(exc),
    )


async def api_key_already_exists_handler(
    request: Request, exc: ApiKeyAlreadyExistsError
) -> JSONResponse:
    """Handle ApiKeyAlreadyExistsError -> 409."""
    return _create_error_response(
        status_code=409,
        error="api_key_already_exists",
        detail=str(exc),
    )


async def api_key_already_revoked_handler(
    request: Request, exc: ApiKeyAlreadyRevokedError
) -> JSONResponse:
    """Handle ApiKeyAlreadyRevokedError -> 409."""
    return _create_error_response(
        status_code=409,
        error="api_key_already_revoked",
        detail=str(exc),
    )


async def bank_endpoint_not_found_handler(
    request: Request, exc: BankEndpointNotFoundError
) -> JSONResponse:
    """Handle BankEndpointNotFoundError -> 404."""
    return _create_error_response(
        status_code=404,
        error="bank_endpoint_not_found",
        detail=str(exc),
    )


async def bank_endpoint_already_exists_handler(
    request: Request, exc: BankEndpointAlreadyExistsError
) -> JSONResponse:
    """Handle BankEndpointAlreadyExistsError -> 409."""
    return _create_error_response(
        status_code=409,
        error="bank_endpoint_already_exists",
        detail=str(exc),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all domain exception handlers with the FastAPI app."""
    app.add_exception_handler(AccountNotFoundError, account_not_found_handler)
    app.add_exception_handler(AccountHasKeysError, account_has_keys_handler)
    app.add_exception_handler(ApiKeyNotFoundError, api_key_not_found_handler)
    app.add_exception_handler(ApiKeyAlreadyExistsError, api_key_already_exists_handler)
    app.add_exception_handler(
        ApiKeyAlreadyRevokedError, api_key_already_revoked_handler
    )
    app.add_exception_handler(
        BankEndpointNotFoundError, bank_endpoint_not_found_handler
    )
    app.add_exception_handler(
        BankEndpointAlreadyExistsError, bank_endpoint_already_exists_handler
    )
