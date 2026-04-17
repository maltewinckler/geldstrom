"""Unit tests for GET /admin/audit route.

Validates: Requirements 5.5, 5.6
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from gateway_admin.domain.audit import (
    AuditEvent,
    AuditEventType,
    AuditPage,
    AuditQuery,
)
from gateway_admin.presentation.api.routes import router

# ---------------------------------------------------------------------------
# Fake infrastructure
# ---------------------------------------------------------------------------


class FakeAuditQueryRepository:
    def __init__(self, events: list[AuditEvent] | None = None) -> None:
        self._events = list(events or [])

    async def query(self, q: AuditQuery) -> AuditPage:
        results = list(self._events)
        # apply ordering (desc)
        results.sort(key=lambda e: e.occurred_at, reverse=True)
        total = len(results)
        start = (q.page - 1) * q.page_size
        end = start + q.page_size
        return AuditPage(
            events=results[start:end],
            total=total,
            page=q.page,
            page_size=q.page_size,
        )


class FakeRepoFactory:
    def __init__(self, audit_repo: FakeAuditQueryRepository) -> None:
        self.audit = audit_repo


# ---------------------------------------------------------------------------
# App fixture
# ---------------------------------------------------------------------------


def _make_app(repo_factory: FakeRepoFactory) -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/admin")
    app.state.repo_factory = repo_factory
    return app


@pytest.fixture
def audit_repo() -> FakeAuditQueryRepository:
    return FakeAuditQueryRepository()


@pytest.fixture
def client(audit_repo: FakeAuditQueryRepository) -> TestClient:
    app = _make_app(FakeRepoFactory(audit_repo))
    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _event(
    *,
    event_type: AuditEventType = AuditEventType.CONSUMER_AUTHENTICATED,
    consumer_id: UUID | None = None,
    occurred_at: datetime | None = None,
) -> AuditEvent:
    return AuditEvent(
        event_id=uuid4(),
        event_type=event_type,
        consumer_id=consumer_id or uuid4(),
        occurred_at=occurred_at or datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_invalid_consumer_id_returns_422(client: TestClient) -> None:
    """Returns 422 for invalid consumer_id UUID string. Validates: Requirement 5.6"""
    response = client.get("/admin/audit", params={"consumer_id": "not-a-uuid"})
    assert response.status_code == 422


def test_page_size_above_200_returns_422(client: TestClient) -> None:
    """Returns 422 for page_size > 200. Validates: Requirement 5.6"""
    response = client.get("/admin/audit", params={"page_size": 201})
    assert response.status_code == 422


def test_no_filters_returns_events_ordered_descending(
    audit_repo: FakeAuditQueryRepository,
    client: TestClient,
) -> None:
    """Returns events ordered by occurred_at descending with no filters.

    Validates: Requirements 5.5
    """
    t1 = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
    t2 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    t3 = datetime(2026, 1, 1, 11, 0, tzinfo=UTC)

    audit_repo._events = [
        _event(occurred_at=t1),
        _event(occurred_at=t2),
        _event(occurred_at=t3),
    ]

    response = client.get("/admin/audit")
    assert response.status_code == 200

    body = response.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["page_size"] == 50

    timestamps = [e["occurred_at"] for e in body["events"]]
    assert timestamps == sorted(timestamps, reverse=True), (
        "Events must be ordered descending"
    )


def test_empty_audit_log_returns_empty_page(client: TestClient) -> None:
    """Returns an empty page when no events exist. Validates: Requirement 5.5"""
    response = client.get("/admin/audit")
    assert response.status_code == 200
    body = response.json()
    assert body["events"] == []
    assert body["total"] == 0


def test_response_schema_fields_present(
    audit_repo: FakeAuditQueryRepository,
    client: TestClient,
) -> None:
    """Each event in the response has the expected fields. Validates: Requirement 5.5"""
    cid = uuid4()
    audit_repo._events = [
        _event(
            event_type=AuditEventType.TOKEN_REROLLED,
            consumer_id=cid,
            occurred_at=datetime(2026, 3, 1, 9, 0, tzinfo=UTC),
        )
    ]

    response = client.get("/admin/audit")
    assert response.status_code == 200

    event = response.json()["events"][0]
    assert "event_id" in event
    assert event["event_type"] == "token_rerolled"
    assert event["consumer_id"] == str(cid)
    assert "occurred_at" in event
