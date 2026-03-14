"""Tests for the EvaluateHealth use case."""

from __future__ import annotations

import asyncio

from gateway.application.health.queries.evaluate_health import EvaluateHealthQuery


class StubCheck:
    def __init__(self, healthy: bool, *, raises: bool = False) -> None:
        self._healthy = healthy
        self._raises = raises

    async def __call__(self) -> bool:
        if self._raises:
            raise RuntimeError("boom")
        return self._healthy


def test_evaluate_health_live_returns_ok() -> None:
    use_case = EvaluateHealthQuery({})

    result = asyncio.run(use_case.live())

    assert result == {"status": "ok"}


def test_evaluate_health_ready_returns_ready_when_all_checks_pass() -> None:
    use_case = EvaluateHealthQuery(
        {
            "postgres": StubCheck(True),
            "consumer_cache": StubCheck(True),
        }
    )

    result = asyncio.run(use_case.ready())

    assert result == {
        "status": "ready",
        "checks": {
            "postgres": "ok",
            "consumer_cache": "ok",
        },
    }


def test_evaluate_health_ready_returns_not_ready_when_any_check_fails() -> None:
    use_case = EvaluateHealthQuery(
        {
            "postgres": StubCheck(False),
            "consumer_cache": StubCheck(True),
            "product_key_material": StubCheck(True, raises=True),
        }
    )

    result = asyncio.run(use_case.ready())

    assert result == {
        "status": "not_ready",
        "checks": {
            "postgres": "failed",
            "consumer_cache": "ok",
            "product_key_material": "failed",
        },
    }
