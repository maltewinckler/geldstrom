"""Thin httpx wrapper around the gateway API, including 202-polling."""

from __future__ import annotations

import time
from datetime import UTC, datetime

import httpx
from rich.console import Console

from .credentials import Creds


class GatewayError(Exception):
    def __init__(self, status_code: int, detail: object) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class GatewayClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 30.0) -> None:
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._http = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _banking_body(self, creds: Creds) -> dict:
        return {
            "protocol": "fints",
            "blz": creds.blz,
            "user_id": creds.user_id,
            "password": creds.password,
            "tan_method": creds.tan_method or None,
            "tan_medium": creds.tan_medium or None,
        }

    def _post(self, path: str, body: dict) -> tuple[int, dict]:
        resp = self._http.post(path, json=body)
        if resp.status_code not in (200, 202):
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            raise GatewayError(resp.status_code, detail)
        return resp.status_code, resp.json()

    # ------------------------------------------------------------------
    # Endpoints
    # ------------------------------------------------------------------

    def health(self) -> dict:
        resp = self._http.get("/health/live")
        resp.raise_for_status()
        return resp.json()

    def accounts(self, creds: Creds) -> tuple[int, dict]:
        return self._post("/v1/banking/accounts", self._banking_body(creds))

    def balances(self, creds: Creds) -> tuple[int, dict]:
        return self._post("/v1/banking/balances", self._banking_body(creds))

    def tan_methods(self, creds: Creds) -> tuple[int, dict]:
        return self._post("/v1/banking/tan-methods", self._banking_body(creds))

    def transactions(
        self,
        creds: Creds,
        iban: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[int, dict]:
        body = self._banking_body(creds)
        body["iban"] = iban
        if start_date:
            body["start_date"] = start_date
        if end_date:
            body["end_date"] = end_date
        return self._post("/v1/banking/transactions", body)

    def poll_operation(self, operation_id: str) -> dict:
        resp = self._http.get(f"/v1/banking/operations/{operation_id}")
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # 2FA polling with live spinner
    # ------------------------------------------------------------------

    def wait_for_operation(
        self,
        operation_id: str,
        expires_at: str,
        console: Console,
        poll_interval: int = 5,
    ) -> dict:
        """Poll until the operation reaches a terminal state, showing a spinner.

        Returns the full status dict; callers check ``result["status"]``.
        """
        expires = _parse_dt(expires_at)

        with console.status("", spinner="dots") as status:
            while True:
                now = datetime.now(UTC)
                remaining = max(0, int((expires - now).total_seconds()))
                status.update(
                    f"[yellow]Waiting for 2FA approval on your device… "
                    f"({remaining}s remaining)[/yellow]"
                )

                result = self.poll_operation(operation_id)
                if result["status"] in ("completed", "failed", "expired"):
                    return result

                if remaining <= 0:
                    # Let the server have the final word on expiry
                    return result

                time.sleep(poll_interval)

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> GatewayClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
