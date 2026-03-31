"""PostgreSQL LISTEN/NOTIFY cache invalidation for gateway instances."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from uuid import UUID

import asyncpg
from gateway_contracts.channels import (
    CATALOG_REPLACED_CHANNEL,
    CONSUMER_UPDATED_CHANNEL,
)
from gateway_contracts.payloads import ConsumerUpdatedPayload
from sqlalchemy.engine import URL, make_url

from gateway.domain.banking_gateway import (
    FinTSInstituteRepository,
    InstituteCacheLoader,
)
from gateway.domain.consumer_access import ApiConsumerRepository, ConsumerCache

LISTEN_CHANNELS = (
    CONSUMER_UPDATED_CHANNEL,
    CATALOG_REPLACED_CHANNEL,
)

logger = logging.getLogger(__name__)


class PostgresNotifyListener:
    """Refreshes in-memory caches when PostgreSQL invalidation events arrive."""

    def __init__(
        self,
        *,
        database_url: str,
        consumer_repository: ApiConsumerRepository,
        consumer_cache: ConsumerCache,
        institute_repository: FinTSInstituteRepository,
        institute_cache: InstituteCacheLoader,
        reconnect_backoff_seconds: float = 1.0,
        max_reconnect_backoff_seconds: float = 30.0,
    ) -> None:
        self._database_url = _normalize_database_url(database_url)
        self._consumer_repository = consumer_repository
        self._consumer_cache = consumer_cache
        self._institute_repository = institute_repository
        self._institute_cache = institute_cache
        self._base_backoff_seconds = max(reconnect_backoff_seconds, 0.1)
        self._max_backoff_seconds = max(
            max_reconnect_backoff_seconds, self._base_backoff_seconds
        )
        self._stop_event = asyncio.Event()
        self._ready_event = asyncio.Event()
        self._runner_task: asyncio.Task[None] | None = None
        self._startup_future: asyncio.Future[None] | None = None
        self._connection: asyncpg.Connection | None = None
        self._handler_tasks: set[asyncio.Task[None]] = set()

    async def start(self) -> None:
        """Start the background listener loop if it is not already running."""

        if self._runner_task is not None and not self._runner_task.done():
            if self._startup_future is not None:
                await self._startup_future
            return
        self._stop_event.clear()
        self._ready_event.clear()
        self._startup_future = asyncio.get_running_loop().create_future()
        self._runner_task = asyncio.create_task(self._run(), name="postgres-notify")
        try:
            await self._startup_future
        except Exception:
            await self.stop()
            raise

    async def stop(self) -> None:
        """Stop the background listener loop and close the current connection."""

        self._stop_event.set()
        self._ready_event.clear()
        startup_future = self._startup_future
        if startup_future is not None and not startup_future.done():
            startup_future.cancel()
        connection = self._connection
        if connection is not None and not connection.is_closed():
            await connection.close()

        runner_task = self._runner_task
        self._runner_task = None
        if runner_task is not None:
            runner_task.cancel()
            await asyncio.gather(runner_task, return_exceptions=True)

        if self._handler_tasks:
            await asyncio.gather(*self._handler_tasks, return_exceptions=True)

    async def _run(self) -> None:
        backoff_seconds = self._base_backoff_seconds
        while not self._stop_event.is_set():
            try:
                await self._listen_until_disconnect()
                backoff_seconds = self._base_backoff_seconds
            except Exception as exc:
                startup_future = self._startup_future
                if startup_future is not None and not startup_future.done():
                    startup_future.set_exception(exc)
                if self._stop_event.is_set():
                    break
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=backoff_seconds,
                    )
                backoff_seconds = min(backoff_seconds * 2, self._max_backoff_seconds)

    async def _listen_until_disconnect(self) -> None:
        disconnected = asyncio.Event()
        connection = await asyncpg.connect(
            user=self._database_url.username,
            password=self._database_url.password,
            database=self._database_url.database,
            host=self._database_url.host,
            port=self._database_url.port,
        )
        self._connection = connection
        connection.add_termination_listener(lambda _: disconnected.set())
        try:
            for channel in LISTEN_CHANNELS:
                await connection.add_listener(channel, self._handle_notification)
            startup_future = self._startup_future
            if startup_future is not None and not startup_future.done():
                startup_future.set_result(None)
            self._ready_event.set()
            await _wait_for_first(self._stop_event.wait(), disconnected.wait())
        finally:
            self._ready_event.clear()
            try:
                if not connection.is_closed():
                    for channel in LISTEN_CHANNELS:
                        await connection.remove_listener(
                            channel, self._handle_notification
                        )
                    await connection.close()
            finally:
                if self._connection is connection:
                    self._connection = None

    def _handle_notification(
        self,
        connection: asyncpg.Connection,
        process_id: int,
        channel: str,
        payload: str,
    ) -> None:
        del connection, process_id
        task = asyncio.create_task(
            self._dispatch_notification(channel, payload),
            name=f"postgres-notify:{channel}",
        )
        self._handler_tasks.add(task)
        task.add_done_callback(self._finalize_handler_task)

    def _finalize_handler_task(self, task: asyncio.Task[None]) -> None:
        self._handler_tasks.discard(task)
        try:
            exc = task.exception()
        except asyncio.CancelledError:
            return
        if exc is not None:
            logger.error(
                "Cache refresh handler failed",
                exc_info=exc,
            )

    async def _dispatch_notification(self, channel: str, payload: str) -> None:
        if channel == CONSUMER_UPDATED_CHANNEL:
            try:
                parsed = ConsumerUpdatedPayload.deserialize(payload)
            except (ValueError, KeyError):
                logger.warning("Invalid consumer_updated payload: %s", payload)
                return
            await self._refresh_consumer(parsed)
            return
        if channel == CATALOG_REPLACED_CHANNEL:
            await self._refresh_catalog()
            return

    async def _refresh_consumer(self, payload: ConsumerUpdatedPayload) -> None:
        consumer_id = UUID(payload.consumer_id)
        consumer = await self._consumer_repository.get_by_id(consumer_id)
        if consumer is None:
            await self._consumer_cache.evict(consumer_id)
            return
        await self._consumer_cache.reload_one(consumer)

    async def _refresh_catalog(self) -> None:
        institutes = await self._institute_repository.list_all()
        await self._institute_cache.load(institutes)


def _normalize_database_url(database_url: str) -> URL:
    return make_url(database_url).set(drivername="postgresql")


async def _wait_for_first(*awaitables: object) -> None:
    tasks = [asyncio.create_task(awaitable) for awaitable in awaitables]
    try:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        del done
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
