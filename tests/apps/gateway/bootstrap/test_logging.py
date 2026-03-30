"""Tests for the gateway structured logging configuration."""

from __future__ import annotations

import logging

from gateway.logging_config import _FORBIDDEN_LOG_FIELDS, configure_logging


def test_configure_logging_does_not_raise() -> None:
    configure_logging(json_logs=False, level="WARNING")


def test_json_formatter_emits_valid_json() -> None:
    import json

    configure_logging(json_logs=True, level="DEBUG")
    logger = logging.getLogger("test.logging.json")

    with _capture_log(logger) as handler:
        logger.info("hello world")

    assert handler.records, "expected at least one log record"
    record = handler.records[0]
    # The formatter should produce parseable JSON.
    payload = json.loads(handler.last_formatted)
    assert payload["message"] == "hello world"
    assert payload["level"] == "INFO"


def test_forbidden_fields_are_redacted() -> None:
    from gateway.logging_config import _SecretScrubFilter

    scrub = _SecretScrubFilter()
    for field in _FORBIDDEN_LOG_FIELDS:
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="test",
            args=(),
            exc_info=None,
        )
        setattr(record, field, "secret-value")
        assert scrub.filter(record), (
            f"field {field!r} should keep the record (redact, not drop)"
        )
        assert getattr(record, field) == "[REDACTED]", (
            f"field {field!r} should be redacted"
        )


def test_allowed_extra_fields_pass_through() -> None:
    import json

    configure_logging(json_logs=True, level="DEBUG")
    logger = logging.getLogger("test.logging.allow")

    with _capture_log(logger) as handler:
        logger.info("event", extra={"consumer_id": "abc-123", "count": 5})

    assert handler.records, "expected one record"
    payload = json.loads(handler.last_formatted)
    assert payload.get("consumer_id") == "abc-123"
    assert payload.get("count") == 5


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


class _CapturingHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []
        self.last_formatted: str = ""

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)
        self.last_formatted = self.format(record)


class _capture_log:
    """Context manager that attaches a capturing handler to a logger."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger
        self._handler = _CapturingHandler()

    def __enter__(self) -> _CapturingHandler:
        # The _JsonFormatter / plain text formatter is installed on the root
        # handler by configure_logging(); copy it onto our capturing handler.
        root_handlers = logging.getLogger().handlers
        if root_handlers:
            self._handler.setFormatter(root_handlers[0].formatter)
        # Attach *after* root propagation so we can observe filtered results.
        # We temporarily disable propagation so only our handler runs.
        self._logger.propagate = False
        self._logger.addHandler(self._handler)
        return self._handler

    def __exit__(self, *_: object) -> None:
        self._logger.removeHandler(self._handler)
        self._logger.propagate = True
