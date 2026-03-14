"""Tests for the gateway startup/shutdown lifecycle."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from gateway.lifecycle import run_resume_worker, shutdown, startup

# ---------------------------------------------------------------------------
# startup / shutdown — delegation to factory
# ---------------------------------------------------------------------------


def test_startup_delegates_to_factory() -> None:
    factory = AsyncMock()

    with patch("gateway.lifecycle.get_factory", return_value=factory):
        asyncio.run(startup())

    factory.startup.assert_awaited_once()


def test_shutdown_delegates_to_factory() -> None:
    factory = AsyncMock()

    with patch("gateway.lifecycle.get_factory", return_value=factory):
        asyncio.run(shutdown())

    factory.shutdown.assert_awaited_once()


# ---------------------------------------------------------------------------
# resume worker
# ---------------------------------------------------------------------------


def test_run_resume_worker_stops_on_cancellation() -> None:
    from gateway.application.banking.commands.resume_pending_operations import (
        ResumePendingOperationsCommand,
    )
    from gateway.application.banking.dtos.resume_pending_operations import ResumeSummary

    use_case = AsyncMock(return_value=ResumeSummary())

    async def _run() -> None:
        task = asyncio.create_task(run_resume_worker(interval_seconds=0.01))
        await asyncio.sleep(0.05)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    with patch("gateway.lifecycle.get_factory"):
        with patch.object(ResumePendingOperationsCommand, "from_factory", return_value=use_case):
            asyncio.run(_run())

    assert use_case.await_count >= 1
