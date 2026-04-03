"""Middleware that echoes or generates a ``X-Request-ID`` header."""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_HEADER = "X-Request-ID"


def _valid_request_id(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Echo the incoming ``X-Request-ID`` (if it is a valid UUID) or generate a fresh one."""

    async def dispatch(self, request: Request, call_next: object) -> Response:
        raw = request.headers.get(_HEADER, "")
        request_id = raw if _valid_request_id(raw) else str(uuid.uuid4())
        response: Response = await call_next(request)  # type: ignore[arg-type]
        response.headers[_HEADER] = request_id
        return response
