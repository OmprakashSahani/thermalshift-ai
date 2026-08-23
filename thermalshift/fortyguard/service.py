"""High-level composition of FortyGuard submission and polling."""

import asyncio
from collections.abc import Awaitable, Callable, Iterable, Mapping
from typing import Any, Protocol

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


async def create_heatmap(
    client: HeatmapClient,
    payload: Mapping[str, Any],
    *,
    delays: Iterable[float] = (3.0, 6.0, 12.0),
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> HeatmapResult:
    """Submit a heatmap once, wait for completion, and return its result."""
    activity_id = await client.submit_heatmap(payload)
    status = await wait_for_completion(client, activity_id, delays=delays, sleep=sleep)
    if status.result is None:
        raise RuntimeError("Completed FortyGuard activity is missing its result")
    return status.result
