"""Middleware that sets ``Cache-Control: no-store`` on all non-health routes."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_NO_STORE_HEADER = "no-store"
_HEALTH_PREFIX = "/health"


class CacheControlMiddleware(BaseHTTPMiddleware):
    """Prevent caching of sensitive API responses."""

    async def dispatch(self, request: Request, call_next: object) -> Response:
        response: Response = await call_next(request)
        if not request.url.path.startswith(_HEALTH_PREFIX):
            response.headers["Cache-Control"] = _NO_STORE_HEADER
        return response
