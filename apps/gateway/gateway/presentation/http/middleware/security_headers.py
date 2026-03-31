"""Middleware that sets standard defence-in-depth response headers."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    # Prevent browsers from loading any sub-resources from API responses.
    "Content-Security-Policy": "default-src 'none'",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Append security headers to every response."""

    async def dispatch(self, request: Request, call_next: object) -> Response:
        response: Response = await call_next(request)
        for header, value in _SECURITY_HEADERS.items():
            response.headers[header] = value
        return response
