"""High-level composition of FortyGuard submission and polling."""

import asyncio
from collections.abc import Awaitable, Callable, Iterable, Mapping
from typing import Any, Protocol

from thermalshift.fortyguard.client import FortyGuardHTTPError, FortyGuardResponseError
from thermalshift.fortyguard.models import ActivityStatus, HeatmapResult
from thermalshift.fortyguard.poller import wait_for_completion


class HeatmapClient(Protocol):
    """Client interface needed to create and poll a heatmap."""

    async def submit_heatmap(self, payload: Mapping[str, Any]) -> str:
        """Submit a heatmap and return its activity ID."""
        ...

    async def get_status(self, activity_id: str) -> ActivityStatus:
        """Return an activity status."""
        ...


class FortyGuardStatusRequestError(RuntimeError):
    """Safe context for an HTTP or response error after heatmap submission."""

    def __init__(
        self,
        activity_id: str,
        failure_kind: str,
        *,
        status_code: int | None = None,
        response_reason: str | None = None,
        validation_paths: tuple[tuple[str, ...], ...] = (),
    ) -> None:
        if not activity_id.strip():
            raise ValueError("activity_id must not be blank")
        if failure_kind not in {"http_error", "response_error"}:
            raise ValueError("failure_kind must be http_error or response_error")
        self.activity_id = activity_id
        self.failure_kind = failure_kind
        self.status_code = status_code
        self.response_reason = response_reason
        self.validation_paths = validation_paths
        super().__init__(f"FortyGuard status request failed for activity {activity_id}")

async def create_heatmap(
    client: HeatmapClient,
    payload: Mapping[str, Any],
    *,
    delays: Iterable[float] = (3.0, 6.0, 12.0),
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> HeatmapResult:
    """Submit a heatmap once, wait for completion, and return its result."""
    activity_id = await client.submit_heatmap(payload)
    try:
        status = await wait_for_completion(client, activity_id, delays=delays, sleep=sleep)
    except FortyGuardHTTPError as exc:
        raise FortyGuardStatusRequestError(
            activity_id, "http_error", status_code=exc.status_code
        ) from exc
    except FortyGuardResponseError as exc:
        raise FortyGuardStatusRequestError(
            activity_id,
            "response_error",
            response_reason=exc.reason_code,
            validation_paths=exc.validation_paths,
        ) from exc
    if status.result is None:
        raise RuntimeError("Completed FortyGuard activity is missing its result")
    return status.result
