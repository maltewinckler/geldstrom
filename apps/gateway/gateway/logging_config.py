"""Structured, secret-safe logging configuration for the gateway backend."""

from __future__ import annotations

import logging
import logging.config
from typing import Any

# Fields that must never appear in log records.
_FORBIDDEN_LOG_FIELDS: frozenset[str] = frozenset(
    {
        "password",
        "api_key",
        "raw_api_key",
        "product_key",
        "master_key",
        "encrypted_product_key",
        "authorization",
        "cookie",
        "secret",
        "token",
        "credentials",
    }
)


class _SecretScrubFilter(logging.Filter):
    """Redact forbidden fields on any log record rather than dropping it."""

    def filter(self, record: logging.LogRecord) -> bool:
        for field in _FORBIDDEN_LOG_FIELDS:
            if hasattr(record, field):
                object.__setattr__(record, field, "[REDACTED]")
        return True


class _JsonFormatter(logging.Formatter):
    """Minimal JSON-lines log formatter — no third-party dependency."""

    def format(self, record: logging.LogRecord) -> str:
        import json

        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        # Include any extra fields attached via the ``extra=`` kwarg.
        _STANDARD_ATTRS = logging.LogRecord.__dict__.keys() | {
            "message",
            "asctime",
            "levelname",
            "levelno",
            "name",
            "msg",
            "args",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "taskName",
            "pathname",
            "filename",
            "module",
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS:
                payload[key] = value
        return json.dumps(payload, default=str)


def configure_logging(*, json_logs: bool = True, level: str = "INFO") -> None:
    formatter: dict[str, Any]
    if json_logs:
        formatter = {
            "()": _JsonFormatter,
        }
    else:
        formatter = {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        }

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "scrub_secrets": {
                    "()": _SecretScrubFilter,
                }
            },
            "formatters": {
                "default": formatter,
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "filters": ["scrub_secrets"],
                }
            },
            "root": {
                "level": level,
                "handlers": ["console"],
            },
            # Keep third-party loggers quieter by default.
            "loggers": {
                "uvicorn": {"level": "WARNING", "propagate": True},
                "uvicorn.error": {"level": "WARNING", "propagate": True},
                "uvicorn.access": {"level": "WARNING", "propagate": True},
                "sqlalchemy.engine": {"level": "WARNING", "propagate": True},
            },
        }
    )
