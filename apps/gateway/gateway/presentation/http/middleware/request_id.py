"""Middleware that echoes or generates a ``X-Request-ID`` header."""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Echo the incoming ``X-Request-ID`` or attach a freshly generated UUID."""

    async def dispatch(self, request: Request, call_next: object) -> Response:
        request_id = request.headers.get(_HEADER) or str(uuid.uuid4())
        response: Response = await call_next(request)  # type: ignore[arg-type]
        response.headers[_HEADER] = request_id
        return response
