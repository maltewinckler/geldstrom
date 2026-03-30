"""Exception handlers that translate application errors into HTTP responses."""

from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from gateway.application.common import (
    ApplicationError,
    BankUpstreamUnavailableError,
    ForbiddenError,
    InstitutionNotFoundError,
    InternalError,
    OperationExpiredError,
    OperationNotFoundError,
    UnauthorizedError,
    UnsupportedProtocolError,
    ValidationError,
)

from ..schemas.errors import ErrorResponse

logger = logging.getLogger(__name__)

_CODE_TO_STATUS: dict[type[ApplicationError], int] = {
    UnauthorizedError: 401,
    ForbiddenError: 403,
    ValidationError: 422,
    UnsupportedProtocolError: 422,
    InstitutionNotFoundError: 404,
    OperationNotFoundError: 404,
    OperationExpiredError: 404,
    BankUpstreamUnavailableError: 502,
    InternalError: 500,
}


async def application_error_handler(
    request: Request,
    exc: ApplicationError,
) -> JSONResponse:
    """Translate an :class:`ApplicationError` into a JSON HTTP response."""
    status = _CODE_TO_STATUS.get(type(exc), 500)
    if status >= 500:
        logger.exception("Unhandled application error", exc_info=exc)
    body = ErrorResponse(error=exc.code.value, message=exc.message)
    return JSONResponse(status_code=status, content=body.model_dump())
