"""Tests for bounded FortyGuard activity polling."""

from collections.abc import Sequence

import pytest

from tests.test_fortyguard_models import completed_data
from thermalshift.fortyguard.models import ActivityStatus
from thermalshift.fortyguard.poller import (
    DEFAULT_MAX_STATUS_CHECKS,
    DEFAULT_STATUS_POLL_INTERVAL_SECONDS,
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
        poll_interval_seconds=0.25,
        max_status_checks=2,
        sleep=sleep,
    )

    assert result.status == "Completed"
    assert sleep.delays == [0.25]


@pytest.mark.asyncio
async def test_default_policy_permits_exactly_120_gets_and_119_sleeps() -> None:
    sleep = SleepRecorder()
    client = FakeStatusClient([status("Processing")] * DEFAULT_MAX_STATUS_CHECKS)

    with pytest.raises(FortyGuardPollingTimeout):
        await wait_for_completion(client, "activity-123", sleep=sleep)

    assert len(client.activity_ids) == DEFAULT_MAX_STATUS_CHECKS == 120
    assert len(sleep.delays) == DEFAULT_MAX_STATUS_CHECKS - 1
    assert set(sleep.delays) == {DEFAULT_STATUS_POLL_INTERVAL_SECONDS}


@pytest.mark.asyncio
async def test_failed_status_raises() -> None:
    secret = "api-secret-must-not-appear"
    with pytest.raises(FortyGuardActivityFailed) as caught:
        await wait_for_completion(FakeStatusClient([status("FAILED")]), "activity-123")

    assert caught.value.activity_id == "activity-123"
    assert str(caught.value) == "FortyGuard activity activity-123 failed"
    assert secret not in str(caught.value)


@pytest.mark.asyncio
async def test_blank_activity_id_is_rejected_before_status_request() -> None:
    client = FakeStatusClient([])
    with pytest.raises(ValueError, match="must not be blank"):
        await wait_for_completion(client, " ")
    assert client.activity_ids == []


@pytest.mark.asyncio
async def test_timeout_after_n_checks_retains_activity_id() -> None:
    sleep = SleepRecorder()
    client = FakeStatusClient([status("Processing")] * 3)

    with pytest.raises(FortyGuardPollingTimeout) as caught:
        await wait_for_completion(
            client,
            "activity-123",
            poll_interval_seconds=1.0,
            max_status_checks=3,
            sleep=sleep,
        )

    assert caught.value.activity_id == "activity-123"
    assert client.activity_ids == ["activity-123"] * 3
    assert sleep.delays == [1.0, 1.0]


@pytest.mark.asyncio
async def test_one_maximum_check_performs_one_get_and_zero_sleeps() -> None:
    sleep = SleepRecorder()
    client = FakeStatusClient([status("Processing")])

    with pytest.raises(FortyGuardPollingTimeout) as caught:
        await wait_for_completion(
            client, "activity-123", max_status_checks=1, sleep=sleep
        )

    assert caught.value.activity_id == "activity-123"
    assert client.activity_ids == ["activity-123"]
    assert sleep.delays == []


@pytest.mark.asyncio
async def test_completed_without_result_raises() -> None:
    with pytest.raises(FortyGuardPollingError, match="missing its result"):
        await wait_for_completion(FakeStatusClient([status("Completed")]), "activity-123")


@pytest.mark.asyncio
async def test_unknown_status_raises() -> None:
    with pytest.raises(FortyGuardPollingError, match="Unknown"):
        await wait_for_completion(FakeStatusClient([status("Queued")]), "activity-123")


@pytest.mark.asyncio
async def test_negative_interval_is_rejected_before_status_request() -> None:
    client = FakeStatusClient([])

    with pytest.raises(ValueError, match="must not be negative"):
        await wait_for_completion(client, "activity-123", poll_interval_seconds=-1.0)

    assert client.activity_ids == []


@pytest.mark.asyncio
async def test_zero_maximum_checks_is_rejected_before_status_request() -> None:
    client = FakeStatusClient([])

    with pytest.raises(ValueError, match="at least 1"):
        await wait_for_completion(client, "activity-123", max_status_checks=0)

    assert client.activity_ids == []
