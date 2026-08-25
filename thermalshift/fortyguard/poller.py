"""Bounded asynchronous polling for FortyGuard activities."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import Protocol

from thermalshift.fortyguard.models import ActivityStatus

DEFAULT_STATUS_POLL_INTERVAL_SECONDS = 5.0
DEFAULT_MAX_STATUS_CHECKS = 120


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
    """Raised when an activity remains processing after all allowed checks."""

    def __init__(self, activity_id: str) -> None:
        if not activity_id.strip():
            raise ValueError("activity_id must not be blank")
        self.activity_id = activity_id
        super().__init__(f"Polling ended before FortyGuard activity {activity_id} completed")


async def wait_for_completion(
    client: StatusClient,
    activity_id: str,
    *,
    poll_interval_seconds: float = DEFAULT_STATUS_POLL_INTERVAL_SECONDS,
    max_status_checks: int = DEFAULT_MAX_STATUS_CHECKS,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> ActivityStatus:
    """Poll an activity to completion with a finite number of status checks."""
    if not activity_id.strip():
        raise ValueError("activity_id must not be blank")
    if poll_interval_seconds < 0:
        raise ValueError("poll_interval_seconds must not be negative")
    if max_status_checks < 1:
        raise ValueError("max_status_checks must be at least 1")

    for check_number in range(max_status_checks):
        status = await client.get_status(activity_id)
        result = _evaluate(status, activity_id)
        if result is not None:
            return result
        if check_number < max_status_checks - 1:
            await sleep(poll_interval_seconds)
    raise FortyGuardPollingTimeout(activity_id)


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
