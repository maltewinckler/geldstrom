"""In-memory registry for pending decoupled TAN client handles."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime

from gateway.domain.banking_gateway.operations import OperationType
from geldstrom.clients.fints3_decoupled import FinTS3ClientDecoupled

logger = logging.getLogger(__name__)


@dataclass
class PendingHandle:
    """A live client with a pending TAN challenge."""

    client: FinTS3ClientDecoupled
    operation_type: OperationType
    expires_at: datetime
    extra_meta: dict = field(default_factory=dict)


class PendingClientRegistry:
    """Thread-safe in-memory store for clients awaiting TAN approval."""

    def __init__(self) -> None:
        self._handles: dict[str, PendingHandle] = {}
        self._lock = threading.Lock()

    def store(self, handle_id: str, handle: PendingHandle) -> None:
        with self._lock:
            self._handles[handle_id] = handle

    def get(self, handle_id: str) -> PendingHandle | None:
        with self._lock:
            return self._handles.get(handle_id)

    def remove(self, handle_id: str) -> PendingHandle | None:
        with self._lock:
            handle = self._handles.pop(handle_id, None)
        if handle is not None:
            handle.client.cleanup_pending()
        return handle

    def cleanup_expired(self, now: datetime) -> int:
        expired_ids: list[str] = []
        with self._lock:
            for hid, handle in self._handles.items():
                if handle.expires_at <= now:
                    expired_ids.append(hid)
            expired_handles = [self._handles.pop(hid) for hid in expired_ids]

        for handle in expired_handles:
            try:
                handle.client.cleanup_pending()
            except Exception:
                logger.debug("Error cleaning up expired handle", exc_info=True)

        return len(expired_ids)
