"""E2E: POST /v1/banking/tan-methods — retrieve available TAN methods.

TAN methods are fetched without a 2FA challenge (it's a metadata call).
The response must list at least one method, and the configured method from
.env must appear in the list.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

_EXPECTED_PENDING_FIELDS = {
    "status",
    "operation_id",
    "expires_at",
    "polling_interval_seconds",
}
_EXPECTED_COMPLETED_FIELDS = {"status", "methods"}
# The router serializes TanMethod domain objects as {method_id, display_name}
_EXPECTED_METHOD_FIELDS = {"method_id", "display_name"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tan_methods_body(creds: dict[str, str]) -> dict:
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


def _assert_completed_schema(body: dict, configured_tan_method: str) -> None:
    missing = _EXPECTED_COMPLETED_FIELDS - body.keys()
    assert not missing, f"200 response missing fields: {missing}"
    assert body["status"] == "completed"

    methods = body["methods"]
    assert isinstance(methods, list), "methods must be a list"
    assert len(methods) > 0, (
        "No TAN methods returned. "
        "If the list is empty this likely indicates a silently swallowed backend error."
    )

    for method in methods:
        missing_fields = _EXPECTED_METHOD_FIELDS - method.keys()
        assert not missing_fields, (
            f"TAN method missing fields {missing_fields}: {method}"
        )
        assert isinstance(method["method_id"], str) and method["method_id"]
        assert isinstance(method["display_name"], str) and method["display_name"]

    method_ids = {m["method_id"] for m in methods}
    assert configured_tan_method in method_ids, (
        f"Configured TAN method '{configured_tan_method}' not found in returned methods: "
        f"{method_ids}. Check FINTS_TAN_METHOD in .env."
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_get_tan_methods_returns_valid_schema(
    app_client: TestClient,
    e2e_api_key: str,
    e2e_credentials: dict[str, str],
) -> None:
    """get_tan_methods returns a non-empty list containing the configured TAN method."""
    resp = app_client.post(
        "/v1/banking/tan-methods",
        headers={"Authorization": f"Bearer {e2e_api_key}"},
        json=_tan_methods_body(e2e_credentials),
    )

    assert resp.status_code in (200, 202), (
        f"Unexpected HTTP status {resp.status_code}: {resp.text}"
    )

    body = resp.json()

    if resp.status_code == 200:
        _assert_completed_schema(body, e2e_credentials["tan_method"])
    else:
        _assert_pending_schema(body)
