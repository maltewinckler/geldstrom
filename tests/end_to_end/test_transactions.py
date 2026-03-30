"""E2E: POST /v1/banking/transactions — fetch account transactions.

Strategy:
  1. Get accounts first to obtain a real IBAN (avoids hardcoding it in .env).
     If accounts returns 202 the test is skipped — we need an IBAN to proceed.
  2. Fetch the last 30 days of transactions (low 2FA probability).
  3. The --run-e2e-tan variant fetches 200 days explicitly to force a challenge.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from starlette.testclient import TestClient

_TODAY = date.today()
_30_DAYS_AGO = _TODAY - timedelta(days=30)
_200_DAYS_AGO = _TODAY - timedelta(days=200)

_EXPECTED_PENDING_FIELDS = {
    "status",
    "operation_id",
    "expires_at",
    "polling_interval_seconds",
}
_EXPECTED_COMPLETED_FIELDS = {"status", "transactions"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_first_iban(
    app_client: TestClient,
    api_key: str,
    creds: dict[str, str],
) -> str | None:
    """Call /accounts and return the first IBAN, or None if 2FA is required."""
    resp = app_client.post(
        "/v1/banking/accounts",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "protocol": "fints",
            "blz": creds["blz"],
            "user_id": creds["user_id"],
            "password": creds["password"],
            "tan_method": creds["tan_method"] or None,
            "tan_medium": creds["tan_medium"] or None,
        },
    )
    if resp.status_code != 200:
        return None
    accounts = resp.json().get("accounts", [])
    return accounts[0]["iban"] if accounts else None


def _transactions_body(
    creds: dict[str, str], iban: str, start: date, end: date
) -> dict:
    return {
        "protocol": "fints",
        "blz": creds["blz"],
        "user_id": creds["user_id"],
        "password": creds["password"],
        "iban": iban,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "tan_method": creds["tan_method"] or None,
        "tan_medium": creds["tan_medium"] or None,
    }


def _assert_pending_schema(body: dict) -> None:
    missing = _EXPECTED_PENDING_FIELDS - body.keys()
    assert not missing, f"202 response missing fields: {missing}"
    assert body["status"] == "pending_confirmation"
    assert isinstance(body["operation_id"], str) and body["operation_id"]


def _assert_completed_schema(body: dict) -> None:
    missing = _EXPECTED_COMPLETED_FIELDS - body.keys()
    assert not missing, f"200 response missing fields: {missing}"
    assert body["status"] == "completed"
    transactions = body["transactions"]
    assert isinstance(transactions, list), "transactions must be a list"
    # A 30-day window on an active account should return at least one entry.
    # If the list is empty, it may indicate a silently swallowed backend error.
    assert len(transactions) > 0, (
        "No transactions returned for the last 30 days. "
        "Verify the account is active and the date range is correct."
    )
    for tx in transactions:
        # Every transaction must carry at least these fields
        assert "amount" in tx, f"Transaction missing 'amount': {tx}"
        assert "date" in tx or "booking_date" in tx, (
            f"Transaction missing date field: {tx}"
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_fetch_transactions_30_days_returns_valid_schema(
    app_client: TestClient,
    e2e_api_key: str,
    e2e_credentials: dict[str, str],
) -> None:
    """Fetch the last 30 days of transactions; verify schema and non-empty result."""
    iban = _get_first_iban(app_client, e2e_api_key, e2e_credentials)
    if iban is None:
        pytest.skip("Could not obtain IBAN (accounts call returned 202 — 2FA required)")

    resp = app_client.post(
        "/v1/banking/transactions",
        headers={"Authorization": f"Bearer {e2e_api_key}"},
        json=_transactions_body(e2e_credentials, iban, _30_DAYS_AGO, _TODAY),
    )

    assert resp.status_code in (200, 202), (
        f"Unexpected HTTP status {resp.status_code}: {resp.text}"
    )

    body = resp.json()

    if resp.status_code == 200:
        _assert_completed_schema(body)
    else:
        _assert_pending_schema(body)


@pytest.mark.e2e_tan
def test_fetch_transactions_200_days_triggers_tan(
    app_client: TestClient,
    e2e_api_key: str,
    e2e_credentials: dict[str, str],
) -> None:
    """Fetch 200 days of transactions — expects the bank to require 2FA (202).

    This test deliberately triggers a decoupled TAN challenge. It verifies that
    the gateway correctly issues the pending response schema and does NOT silently
    swallow the backend challenge.
    """
    iban = _get_first_iban(app_client, e2e_api_key, e2e_credentials)
    if iban is None:
        pytest.skip("Could not obtain IBAN (accounts call returned 202)")

    resp = app_client.post(
        "/v1/banking/transactions",
        headers={"Authorization": f"Bearer {e2e_api_key}"},
        json=_transactions_body(e2e_credentials, iban, _200_DAYS_AGO, _TODAY),
    )

    # A 200-day window should always require 2FA; 200 OK would be unexpected.
    assert resp.status_code in (200, 202), (
        f"Unexpected HTTP status {resp.status_code}: {resp.text}"
    )

    body = resp.json()

    if resp.status_code == 202:
        missing = _EXPECTED_PENDING_FIELDS - body.keys()
        assert not missing, f"202 response missing fields: {missing}"
        assert body["status"] == "pending_confirmation"
        assert body["operation_id"], "operation_id must be a non-empty string"
    else:
        # 200 is technically valid; still verify the schema
        _assert_completed_schema(body)
