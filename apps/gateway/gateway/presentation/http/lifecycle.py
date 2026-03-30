"""Startup and shutdown lifecycle for the gateway backend."""

from __future__ import annotations

import asyncio
import logging

from gateway.application.banking.commands.resume_pending_operations import (
    ResumePendingOperationsCommand,
)
from gateway.presentation.http.dependencies import get_factory

_logger = logging.getLogger(__name__)


async def startup() -> None:
    await get_factory().startup()


async def shutdown() -> None:
    await get_factory().shutdown()


async def run_resume_worker(*, interval_seconds: float = 5.0) -> None:
    """Long-running background task that polls pending decoupled sessions.

    Designed to be run as an asyncio task inside the FastAPI lifespan.
    Cancellation is the expected stop signal.
    """
    use_case = ResumePendingOperationsCommand.from_factory(get_factory())
    while True:
        try:
            summary = await use_case()
            if summary.completed_count or summary.failed_count or summary.expired_count:
                _logger.info(
                    "resume worker pass",
                    extra={
                        "completed": summary.completed_count,
                        "failed": summary.failed_count,
                        "expired": summary.expired_count,
                        "pending": summary.pending_count,
                    },
                )
        except asyncio.CancelledError:
            break
        except Exception:
            _logger.exception("resume worker encountered an error")
        await asyncio.sleep(interval_seconds)
