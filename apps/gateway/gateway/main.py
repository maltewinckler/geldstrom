"""Entry point for the banking gateway HTTP server."""

from __future__ import annotations

import uvicorn

from gateway.config import Settings
from gateway.logging_config import configure_logging


def main():
    settings = Settings()
    configure_logging(json_logs=settings.json_logs, level=settings.log_level)

    uvicorn.run(
        "gateway.presentation.http.api:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        log_config=None,  # logging already configured above
    )


if __name__ == "__main__":
    main()
