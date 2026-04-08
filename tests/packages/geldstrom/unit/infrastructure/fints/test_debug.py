"""Tests for FinTS debugging helpers."""

from __future__ import annotations

import json
import logging
from contextlib import contextmanager

from geldstrom.infrastructure.fints import debug as debug_module


def test_parser_debugger_capture_collects_parser_warnings() -> None:
    debugger = debug_module.ParserDebugger()
    parser_logger = logging.getLogger("geldstrom.infrastructure.fints.protocol.parser")

    with debugger.capture():
        parser_logger.warning("captured warning")

    assert "captured warning" in debugger.report.warnings


def test_parser_debugger_save_report_writes_json(tmp_path) -> None:
    debugger = debug_module.ParserDebugger()
    debugger.report.add_warning("saved warning")

    report_path = debugger.save_report(tmp_path / "report.json")

    payload = json.loads(report_path.read_text())
    assert payload["warnings"] == ["saved warning"]


def test_capture_bank_response_writes_expected_files(tmp_path, monkeypatch) -> None:
    class _FakeSequence:
        def __init__(self, payload: bytes) -> None:
            self._payload = payload

        def serialize(self) -> bytes:
            return self._payload

    class _FakeParameters:
        def __init__(self) -> None:
            self.bpd = _FakeSequence(b"invalid-bpd")
            self.upd = _FakeSequence(b"invalid-upd")
            self.bpd_version = 3
            self.upd_version = 7

    class _FakeContext:
        def __init__(self) -> None:
            self.parameters = _FakeParameters()
            self.dialog = object()

    class _FakeHelper:
        def __init__(self, credentials) -> None:
            self.credentials = credentials

        @contextmanager
        def connect(self, _state):
            yield _FakeContext()

    monkeypatch.setattr(
        "geldstrom.infrastructure.fints.support.connection.FinTSConnectionHelper",
        _FakeHelper,
    )

    summary = debug_module.capture_bank_response(tmp_path, credentials=object())

    assert summary["bpd_version"] == 3
    assert summary["upd_version"] == 7
    assert set(summary["files"]) == {
        "bpd.bin",
        "upd.bin",
        "summary.json",
        "parser_report.json",
    }
    for file_name in summary["files"]:
        assert (tmp_path / file_name).exists()
