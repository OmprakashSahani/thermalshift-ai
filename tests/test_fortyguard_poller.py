"""Tests for bounded FortyGuard activity polling."""

from collections.abc import Sequence

import pytest

from tests.test_fortyguard_models import completed_data
from thermalshift.fortyguard.models import ActivityStatus
from thermalshift.fortyguard.poller import (
    FortyGuardActivityFailed,
    FortyGuardPollingError,
    FortyGuardPollingTimeout,
    wait_for_completion,
)


def completed_status() -> ActivityStatus:
    return ActivityStatus.model_validate(completed_data())


class FakeStatusClient:
    def __init__(self, statuses: Sequence[ActivityStatus]) -> None:
        self._statuses = iter(statuses)
        self.activity_ids: list[str] = []

    async def get_status(self, activity_id: str) -> ActivityStatus:
        self.activity_ids.append(activity_id)
        return next(self._statuses)


class SleepRecorder:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


def status(state: str) -> ActivityStatus:
    return ActivityStatus(activity_id="activity-123", status=state)


@pytest.mark.asyncio
async def test_immediate_completion_does_not_sleep() -> None:
    sleep = SleepRecorder()

    result = await wait_for_completion(
        FakeStatusClient([completed_status()]), "activity-123", sleep=sleep
    )

    assert result.result is not None
    assert sleep.delays == []


@pytest.mark.asyncio
async def test_processing_then_completed() -> None:
    sleep = SleepRecorder()

    result = await wait_for_completion(
        FakeStatusClient([status("processing"), completed_status()]),
        "activity-123",
        delays=(3.0,),
        sleep=sleep,
    )

    assert result.status == "Completed"
    assert sleep.delays == [3.0]


@pytest.mark.asyncio
async def test_full_default_delay_sequence() -> None:
    sleep = SleepRecorder()
    client = FakeStatusClient([status("Processing")] * 3 + [completed_status()])

    await wait_for_completion(client, "activity-123", sleep=sleep)

    assert sleep.delays == [3.0, 6.0, 12.0]


@pytest.mark.asyncio
async def test_failed_status_raises() -> None:
    with pytest.raises(FortyGuardActivityFailed):
        await wait_for_completion(FakeStatusClient([status("FAILED")]), "activity-123")


@pytest.mark.asyncio
async def test_timeout_raises_after_delays() -> None:
    sleep = SleepRecorder()
    client = FakeStatusClient([status("Processing"), status("Processing")])

    with pytest.raises(FortyGuardPollingTimeout):
        await wait_for_completion(client, "activity-123", delays=(1.0,), sleep=sleep)

    assert sleep.delays == [1.0]


@pytest.mark.asyncio
async def test_completed_without_result_raises() -> None:
    with pytest.raises(FortyGuardPollingError, match="missing its result"):
        await wait_for_completion(FakeStatusClient([status("Completed")]), "activity-123")


@pytest.mark.asyncio
async def test_unknown_status_raises() -> None:
    with pytest.raises(FortyGuardPollingError, match="Unknown"):
        await wait_for_completion(FakeStatusClient([status("Queued")]), "activity-123")


@pytest.mark.asyncio
async def test_negative_delay_is_rejected_before_status_request() -> None:
    client = FakeStatusClient([])

    with pytest.raises(ValueError, match="must not be negative"):
        await wait_for_completion(client, "activity-123", delays=(3.0, -1.0))

    assert client.activity_ids == []
