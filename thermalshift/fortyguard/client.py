"""Asynchronous HTTP client for the known FortyGuard API contract."""

import math
from collections.abc import Mapping
from dataclasses import dataclass
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

    _REASON_CODES = frozenset(
        {
            "non_json_response",
            "unexpected_envelope",
            "api_error",
            "missing_data",
            "missing_activity_id",
            "malformed_activity_status",
            "completed_missing_result",
        }
    )

    def __init__(
        self,
        reason_code: str,
        *,
        validation_paths: tuple[tuple[str, ...], ...] = (),
    ) -> None:
        if reason_code not in self._REASON_CODES:
            raise ValueError("unsupported FortyGuard response error reason")
        self.reason_code = reason_code
        self.validation_paths = validation_paths
        super().__init__(f"FortyGuard response error: {reason_code}")


@dataclass(frozen=True, slots=True)
class ArrayShapeDiagnostic:
    """Allow-listed type counts for an array without retaining its values."""

    present: bool
    length: int | None
    number_count: int = 0
    null_count: int = 0
    string_count: int = 0
    boolean_count: int = 0
    object_count: int = 0
    array_count: int = 0
    other_count: int = 0
    non_finite_number_count: int = 0


@dataclass(frozen=True, slots=True)
class ActivityStatusShapeDiagnostic:
    """Sanitized structural summary of one raw activity status response."""

    activity_id: str
    returned_activity_id_matches: bool | None
    status: str | None
    result_present: bool
    stats_data_present: bool
    temperature_stats_present: bool
    temperature_minimum_c: int | float | None
    temperature_maximum_c: int | float | None
    temperature_mean_c: int | float | None
    temperature_standard_deviation_c: int | float | None
    normal_distribution_present: bool
    normal_x_axis: ArrayShapeDiagnostic
    normal_y_axis: ArrayShapeDiagnostic


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
            raise FortyGuardResponseError(
                "missing_activity_id", validation_paths=(("activity_id",),)
            )
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
            paths = tuple(
                sorted(
                    {
                        tuple(str(component) for component in error["loc"])
                        for error in exc.errors()
                    }
                )
            )
            raise FortyGuardResponseError(
                "malformed_activity_status", validation_paths=paths
            ) from exc
        if status.status.casefold() == "completed" and status.result is None:
            raise FortyGuardResponseError(
                "completed_missing_result", validation_paths=(("result",),)
            )
        return status

    async def get_status_diagnostic_shape(
        self, activity_id: str
    ) -> ActivityStatusShapeDiagnostic:
        """Read one status and return only allow-listed response-shape metadata."""
        if not activity_id.strip():
            raise ValueError("FortyGuard activity ID must not be blank")
        safe_activity_id = quote(activity_id, safe="")
        response_payload = await self._request("GET", f"/v1/status/{safe_activity_id}")
        data = self._require_data(response_payload)
        return _build_status_shape(activity_id, data)

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
            raise FortyGuardResponseError("non_json_response") from exc

        if not isinstance(payload, dict) or not isinstance(payload.get("error"), bool):
            raise FortyGuardResponseError("unexpected_envelope")
        if payload["error"]:
            raise FortyGuardResponseError("api_error")
        return payload

    @staticmethod
    def _require_data(payload: dict[str, Any]) -> dict[str, Any]:
        data = payload.get("data")
        if not isinstance(data, dict):
            raise FortyGuardResponseError("missing_data")
        return data


def _build_status_shape(
    requested_activity_id: str, data: dict[str, Any]
) -> ActivityStatusShapeDiagnostic:
    returned_id = data.get("activity_id")
    returned_id_matches = (
        returned_id == requested_activity_id if isinstance(returned_id, str) else None
    )
    status_value = data.get("status")
    status = status_value if isinstance(status_value, str) else None
    result = data.get("result")
    result_present = result is not None
    result_object = result if isinstance(result, dict) else None
    stats_data = result_object.get("stats_data") if result_object is not None else None
    stats_data_present = isinstance(stats_data, dict)
    stats_object = stats_data if isinstance(stats_data, dict) else None
    temperature_stats = (
        stats_object.get("temperature_stats") if stats_object is not None else None
    )
    temperature_stats_present = isinstance(temperature_stats, dict)
    temperature_object = temperature_stats if isinstance(temperature_stats, dict) else {}
    distribution = (
        stats_object.get("normal_temperature_distribution")
        if stats_object is not None
        else None
    )
    distribution_present = isinstance(distribution, dict)
    distribution_object = distribution if isinstance(distribution, dict) else {}
    return ActivityStatusShapeDiagnostic(
        activity_id=requested_activity_id,
        returned_activity_id_matches=returned_id_matches,
        status=status,
        result_present=result_present,
        stats_data_present=stats_data_present,
        temperature_stats_present=temperature_stats_present,
        temperature_minimum_c=_finite_number(temperature_object.get("minimum")),
        temperature_maximum_c=_finite_number(temperature_object.get("maximum")),
        temperature_mean_c=_finite_number(temperature_object.get("mean")),
        temperature_standard_deviation_c=_finite_number(
            temperature_object.get("standard_deviation")
        ),
        normal_distribution_present=distribution_present,
        normal_x_axis=_array_shape(distribution_object, "x_axis"),
        normal_y_axis=_array_shape(distribution_object, "y_axis"),
    )


def _finite_number(value: Any) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if math.isfinite(value) else None


def _array_shape(container: dict[str, Any], field_name: str) -> ArrayShapeDiagnostic:
    if field_name not in container:
        return ArrayShapeDiagnostic(present=False, length=None)
    value = container[field_name]
    if not isinstance(value, list):
        return ArrayShapeDiagnostic(present=True, length=None)

    counts = {
        "number_count": 0,
        "null_count": 0,
        "string_count": 0,
        "boolean_count": 0,
        "object_count": 0,
        "array_count": 0,
        "other_count": 0,
        "non_finite_number_count": 0,
    }
    for item in value:
        if item is None:
            counts["null_count"] += 1
        elif isinstance(item, bool):
            counts["boolean_count"] += 1
        elif isinstance(item, (int, float)):
            counts["number_count"] += 1
            if not math.isfinite(item):
                counts["non_finite_number_count"] += 1
        elif isinstance(item, str):
            counts["string_count"] += 1
        elif isinstance(item, dict):
            counts["object_count"] += 1
        elif isinstance(item, list):
            counts["array_count"] += 1
        else:
            counts["other_count"] += 1
    return ArrayShapeDiagnostic(present=True, length=len(value), **counts)
