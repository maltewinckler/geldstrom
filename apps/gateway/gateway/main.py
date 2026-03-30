"""Entry point for the banking gateway HTTP server."""

from __future__ import annotations

import os

import uvicorn

from gateway.logging_config import configure_logging


def main():
    """Configure logging and start the uvicorn server."""
    json_logs = os.getenv("GATEWAY_JSON_LOGS", "true").lower() not in (
        "0",
        "false",
        "no",
    )
    log_level = os.getenv("GATEWAY_LOG_LEVEL", "INFO").upper()
    configure_logging(json_logs=json_logs, level=log_level)

    uvicorn.run(
        "gateway.presentation.http.api:create_app",
        factory=True,
        host=os.getenv("GATEWAY_HOST", "0.0.0.0"),
        port=int(os.getenv("GATEWAY_PORT", "8000")),
        workers=int(os.getenv("GATEWAY_WORKERS", "1")),
        log_config=None,  # logging already configured above
    )


if __name__ == "__main__":
    main()
