"""Log-scrubbing ASGI middleware.

Defence-in-depth measure that sanitises log-bound request representations so
that raw API keys and unparseable bodies never leak into logs or APM tooling.

The middleware creates a *copy* of the request headers for logging purposes —
the original ASGI scope (and therefore the request seen by downstream handlers)
is never modified.

Requirements: 5.3, 5.4, 5.5
"""

from __future__ import annotations

import json
import logging
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

_REDACTED = "[REDACTED]"
_UNPARSEABLE = "[UNPARSEABLE]"
_API_KEY_HEADER = "x-api-key"


class LogScrubberMiddleware(BaseHTTPMiddleware):
    """Intercepts each request, builds a log-safe representation with
    ``X-API-Key`` replaced by ``[REDACTED]`` and unparseable bodies replaced
    by ``[UNPARSEABLE]``, then logs it at DEBUG level.

    The original request object is passed through to the next handler
    completely unmodified.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        # Build a log-safe header dict from the *original* headers without
        # mutating the underlying ASGI scope.
        safe_headers = _scrub_headers(request.headers.items())

        # Attempt to read and parse the body as JSON for logging.
        safe_body = await _scrub_body(request)

        logger.debug(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "headers": safe_headers,
                "body": safe_body,
            },
        )

        # Forward the *original*, unmodified request to the next handler.
        return await call_next(request)


def _scrub_headers(
    header_items: Any,
) -> dict[str, str]:
    """Return a new dict with ``X-API-Key`` values replaced by ``[REDACTED]``."""
    scrubbed: dict[str, str] = {}
    for key, value in header_items:
        if key.lower() == _API_KEY_HEADER:
            scrubbed[key] = _REDACTED
        else:
            scrubbed[key] = value
    return scrubbed


async def _scrub_body(request: Request) -> Any:
    """Try to parse the request body as JSON.

    Returns the parsed object on success, or ``[UNPARSEABLE]`` if the body
    cannot be decoded as valid JSON.
    """
    try:
        raw = await request.body()
        if not raw:
            return None
        return json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _UNPARSEABLE
