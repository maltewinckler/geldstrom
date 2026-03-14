"""Consumer-related result DTOs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from gateway.domain.consumer_access import ApiConsumer, ConsumerStatus


@dataclass(frozen=True)
class ApiConsumerSummary:
    """Sanitized API consumer view for operator-facing flows."""

    consumer_id: str
    email: str
    status: ConsumerStatus
    created_at: datetime
    rotated_at: datetime | None = None


@dataclass(frozen=True)
class ApiConsumerKeyResult:
    """Result envelope for create/rotate flows that reveal a raw key once."""

    consumer: ApiConsumerSummary
    raw_api_key: str


def to_consumer_summary(consumer: ApiConsumer) -> ApiConsumerSummary:
    return ApiConsumerSummary(
        consumer_id=str(consumer.consumer_id),
        email=consumer.email.value,
        status=consumer.status,
        created_at=consumer.created_at,
        rotated_at=consumer.rotated_at,
    )
