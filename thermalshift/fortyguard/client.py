"""Asynchronous HTTP client for the known FortyGuard API contract."""

from collections.abc import Mapping
from typing import Any, Self
from urllib.parse import quote

import httpx
from pydantic import SecretStr, ValidationError

from thermalshift.fortyguard.models import ActivityStatus


class FortyGuardError(RuntimeError):
    """Base exception for FortyGuard integration errors."""


class FortyGuardHTTPError(FortyGuardError):
    """Raised when an HTTP request to FortyGuard fails."""

    def __init__(self, status_code: int | None = None) -> None:
        self.status_code = status_code
        message = (
            f"FortyGuard returned HTTP {status_code}"
            if status_code is not None
            else "FortyGuard request failed"
        )
        super().__init__(message)


class FortyGuardResponseError(FortyGuardError):
    """Raised when FortyGuard returns an error or malformed response."""


class FortyGuardClient:
    """Submit heatmaps and retrieve activity status from FortyGuard."""

    def __init__(
        self,
        api_key: str | SecretStr,
        base_url: str = "https://api.fortyguard.com",
        timeout_seconds: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        key = api_key.get_secret_value() if isinstance(api_key, SecretStr) else api_key
        if not key.strip():
            raise ValueError("FortyGuard API key must not be blank")

        self._api_key = key
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout_seconds,
            transport=transport,
            headers={
                "api-key": key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

    async def __aenter__(self) -> Self:
        """Enter the asynchronous client context."""
        return self

    async def __aexit__(self, *args: object) -> None:
        """Close the HTTP client when leaving its asynchronous context."""
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def submit_heatmap(self, payload: Mapping[str, Any]) -> str:
        """Submit a heatmap request and return its activity identifier."""
        response_payload = await self._request("POST", "/v1/heatmap", json=dict(payload))
        data = self._require_data(response_payload)
        activity_id = data.get("activity_id")
        if not isinstance(activity_id, str) or not activity_id.strip():
            raise FortyGuardResponseError("FortyGuard response is missing a valid activity_id")
        return activity_id

    async def get_status(self, activity_id: str) -> ActivityStatus:
        """Retrieve and validate the status of an activity."""
        if not activity_id.strip():
            raise ValueError("FortyGuard activity ID must not be blank")
        safe_activity_id = quote(activity_id, safe="")
        response_payload = await self._request("GET", f"/v1/status/{safe_activity_id}")
        data = self._require_data(response_payload)
        try:
            status = ActivityStatus.model_validate(data)
        except ValidationError as exc:
            raise FortyGuardResponseError("FortyGuard returned malformed activity status") from exc
        if status.status.casefold() == "completed" and status.result is None:
            raise FortyGuardResponseError("Completed FortyGuard activity is missing its result")
        return status

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = await self._client.request(method, path, **kwargs)
        except httpx.RequestError as exc:
            raise FortyGuardHTTPError() from exc

        if response.is_error:
            raise FortyGuardHTTPError(response.status_code)

        try:
            payload = response.json()
        except ValueError as exc:
            raise FortyGuardResponseError("FortyGuard returned a non-JSON response") from exc

        if not isinstance(payload, dict) or not isinstance(payload.get("error"), bool):
            raise FortyGuardResponseError("FortyGuard returned an unexpected response structure")
        if payload["error"]:
            message = payload.get("message")
            safe_message = message if isinstance(message, str) and message.strip() else "API error"
            safe_message = safe_message.replace(self._api_key, "[REDACTED]")
            raise FortyGuardResponseError(f"FortyGuard API error: {safe_message}")
        return payload

    @staticmethod
    def _require_data(payload: dict[str, Any]) -> dict[str, Any]:
        data = payload.get("data")
        if not isinstance(data, dict):
            raise FortyGuardResponseError("FortyGuard response is missing valid data")
        return data
