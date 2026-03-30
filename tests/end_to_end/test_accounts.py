"""E2E: POST /v1/banking/accounts — list bank accounts.

Normal run (--run-e2e): 30-day-equivalent call, low probability of 2FA.
TAN run   (--run-e2e-tan): same endpoint but verifies the 202+operation_id path
when a decoupled TAN is forced (covered by test_transactions_tan).
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_EXPECTED_ACCOUNT_FIELDS = {"iban"}
_EXPECTED_PENDING_FIELDS = {
    "status",
    "operation_id",
    "expires_at",
    "polling_interval_seconds",
}
_EXPECTED_COMPLETED_FIELDS = {"status", "accounts"}


def _accounts_body(creds: dict[str, str]) -> dict:
    return {
        "protocol": "fints",
        "blz": creds["blz"],
        "user_id": creds["user_id"],
        "password": creds["password"],
        "tan_method": creds["tan_method"] or None,
        "tan_medium": creds["tan_medium"] or None,
    }


def _assert_pending_schema(body: dict) -> None:
    missing = _EXPECTED_PENDING_FIELDS - body.keys()
    assert not missing, f"202 response missing fields: {missing}"
    assert body["status"] == "pending_confirmation"
    assert isinstance(body["operation_id"], str) and body["operation_id"]
    assert isinstance(body["polling_interval_seconds"], int)


def _assert_completed_schema(body: dict) -> None:
    missing = _EXPECTED_COMPLETED_FIELDS - body.keys()
    assert not missing, f"200 response missing fields: {missing}"
    assert body["status"] == "completed"
    accounts = body["accounts"]
    assert isinstance(accounts, list), "accounts must be a list"
    assert len(accounts) > 0, (
        "No accounts returned — expected at least one account. "
        "If the bank returned an empty list this may indicate a silently swallowed error."
    )
    for account in accounts:
        assert "iban" in account, f"Account missing 'iban': {account}"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_list_accounts_returns_valid_schema(
    app_client: TestClient,
    e2e_api_key: str,
    e2e_credentials: dict[str, str],
) -> None:
    """list_accounts returns 200 with accounts or 202 with operation_id.

    Both status codes are valid — 202 means the bank requires a decoupled TAN
    confirmation before the result is ready.
    """
    resp = app_client.post(
        "/v1/banking/accounts",
        headers={"Authorization": f"Bearer {e2e_api_key}"},
        json=_accounts_body(e2e_credentials),
    )

    assert resp.status_code in (200, 202), (
        f"Unexpected HTTP status {resp.status_code}: {resp.text}"
    )

    body = resp.json()

    if resp.status_code == 200:
        _assert_completed_schema(body)
    else:
        _assert_pending_schema(body)


@pytest.mark.e2e
def test_list_accounts_rejects_missing_auth(
    app_client: TestClient,
    e2e_credentials: dict[str, str],
) -> None:
    """Requests without an Authorization header must be rejected with 401."""
    resp = app_client.post(
        "/v1/banking/accounts",
        json=_accounts_body(e2e_credentials),
    )
    assert resp.status_code == 401


@pytest.mark.e2e
def test_list_accounts_rejects_bad_api_key(
    app_client: TestClient,
    e2e_credentials: dict[str, str],
) -> None:
    """A bogus API key must be rejected with 401."""
    resp = app_client.post(
        "/v1/banking/accounts",
        headers={"Authorization": "Bearer totally-wrong-key"},
        json=_accounts_body(e2e_credentials),
    )
    assert resp.status_code == 401
