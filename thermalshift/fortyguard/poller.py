"""Bounded asynchronous polling for FortyGuard activities."""

import asyncio
from collections.abc import Awaitable, Callable, Iterable
from typing import Protocol

from thermalshift.fortyguard.models import ActivityStatus


class StatusClient(Protocol):
    """Client interface needed by the activity poller."""

    async def get_status(self, activity_id: str) -> ActivityStatus:
        """Return the current activity status."""
        ...


class FortyGuardPollingError(RuntimeError):
    """Base exception for invalid or unsuccessful polling outcomes."""


class FortyGuardActivityFailed(FortyGuardPollingError):
    """Raised when FortyGuard reports a failed activity."""

    def __init__(self, activity_id: str) -> None:
        if not activity_id.strip():
            raise ValueError("activity_id must not be blank")
        self.activity_id = activity_id
        super().__init__(f"FortyGuard activity {activity_id} failed")


class FortyGuardPollingTimeout(FortyGuardPollingError):
    """Raised when an activity remains processing after all polling delays."""


async def wait_for_completion(
    client: StatusClient,
    activity_id: str,
    *,
    delays: Iterable[float] = (3.0, 6.0, 12.0),
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> ActivityStatus:
    """Poll an activity to completion using a finite sequence of delays."""
    if not activity_id.strip():
        raise ValueError("activity_id must not be blank")
    polling_delays = tuple(delays)
    if any(delay < 0 for delay in polling_delays):
        raise ValueError("Polling delays must not be negative")

    status = await client.get_status(activity_id)
    for delay in polling_delays:
        result = _evaluate(status, activity_id)
        if result is not None:
            return result
        await sleep(delay)
        status = await client.get_status(activity_id)

    result = _evaluate(status, activity_id)
    if result is not None:
        return result
    raise FortyGuardPollingTimeout("FortyGuard activity did not complete before polling ended")


def _evaluate(status: ActivityStatus, activity_id: str) -> ActivityStatus | None:
    state = status.status.casefold()
    if state == "processing":
        return None
    if state == "completed":
        if status.result is None:
            raise FortyGuardPollingError("Completed FortyGuard activity is missing its result")
        return status
    if state == "failed":
        raise FortyGuardActivityFailed(activity_id)
    raise FortyGuardPollingError(f"Unknown FortyGuard activity status: {status.status!r}")
