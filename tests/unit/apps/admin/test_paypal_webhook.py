"""Unit tests for the admin PayPal webhook endpoint."""

from fastapi.testclient import TestClient

from admin.api.main import app

client = TestClient(app)


def test_paypal_webhook_returns_200() -> None:
    """POST /webhooks/paypal with a body returns HTTP 200."""
    response = client.post(
        "/webhooks/paypal",
        json={"event_type": "BILLING.SUBSCRIPTION.ACTIVATED", "id": "WH-TEST123"},
    )
    assert response.status_code == 200
    assert response.json() == {"received": True}


def test_paypal_webhook_empty_body() -> None:
    """POST /webhooks/paypal with empty body still returns 200 (stub handler)."""
    response = client.post("/webhooks/paypal", json={})
    assert response.status_code == 200
    assert response.json() == {"received": True}
