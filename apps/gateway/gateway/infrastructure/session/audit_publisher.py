"""Log-based audit event publisher.

Implements the AuditEventPublisher port via structured logging.
Emits one INFO-level log entry per AuditEvent with all fields as
structured data. Fire-and-forget — never blocks the HTTP response
and never raises exceptions to the caller.
"""

from __future__ import annotations

import logging

from gateway.domain.session.value_objects.audit import AuditEvent

_logger = logging.getLogger("gateway.audit")


class LogAuditEventPublisher:
    """Implements AuditEventPublisher port via structured logging."""

    async def publish(self, event: AuditEvent) -> None:
        """Emit a structured log entry with all AuditEvent fields."""
        try:
            _logger.info(
                "audit_event",
                extra={
                    "timestamp": event.timestamp.isoformat(),
                    "account_id": event.account_id,
                    "remote_ip": event.remote_ip,
                    "request_type": event.request_type,
                    "protocol": event.protocol.value if event.protocol else None,
                },
            )
        except Exception:
            _logger.warning("Failed to publish audit event", exc_info=True)
