"""Tests for the FortyGuard heatmap service composition."""

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.test_fortyguard_models import completed_data
from thermalshift.fortyguard.client import FortyGuardHTTPError, FortyGuardResponseError
from thermalshift.fortyguard.models import ActivityStatus, HeatmapResult
from thermalshift.fortyguard.poller import FortyGuardPollingTimeout
from thermalshift.fortyguard.service import FortyGuardStatusRequestError, create_heatmap


class FakeHeatmapClient:
    def __init__(
        self,
        statuses: Sequence[ActivityStatus] = (),
        *,
        submit_error: RuntimeError | None = None,
        status_error: RuntimeError | None = None,
    ) -> None:
        self._statuses = iter(statuses)
        self.submit_error = submit_error
        self.status_error = status_error
        self.submissions: list[Mapping[str, Any]] = []
        self.polled_activity_ids: list[str] = []

    async def submit_heatmap(self, payload: Mapping[str, Any]) -> str:
        self.submissions.append(payload)
        if self.submit_error is not None:
            raise self.submit_error
        return "returned-activity-id"

    async def get_status(self, activity_id: str) -> ActivityStatus:
        self.polled_activity_ids.append(activity_id)
        if self.status_error is not None:
            raise self.status_error
        return next(self._statuses)


async def no_sleep(delay: float) -> None:
    return None


def completed_status() -> ActivityStatus:
    payload = completed_data()
    payload["activity_id"] = "returned-activity-id"
    return ActivityStatus.model_validate(payload)


@pytest.mark.asyncio
async def test_service_submits_once_polls_returned_id_and_returns_result() -> None:
    client = FakeHeatmapClient([completed_status()])
    payload = {"request": "value"}

    result = await create_heatmap(client, payload, sleep=no_sleep)

    assert isinstance(result, HeatmapResult)
    assert client.submissions == [payload]
    assert client.polled_activity_ids == ["returned-activity-id"]


@pytest.mark.asyncio
async def test_service_processing_to_completed_without_real_sleep() -> None:
    processing = ActivityStatus(activity_id="returned-activity-id", status="Processing")
    client = FakeHeatmapClient([processing, completed_status()])
    sleeps: list[float] = []

    async def record_sleep(delay: float) -> None:
        sleeps.append(delay)

    result = await create_heatmap(client, {}, delays=(0.25,), sleep=record_sleep)

    assert isinstance(result, HeatmapResult)
    assert sleeps == [0.25]
    assert len(client.submissions) == 1


@pytest.mark.asyncio
async def test_post_submission_http_error_retains_activity_and_status() -> None:
    client = FakeHeatmapClient(status_error=FortyGuardHTTPError(429))

    with pytest.raises(FortyGuardStatusRequestError) as caught:
        await create_heatmap(client, {}, sleep=no_sleep)

    assert caught.value.activity_id == "returned-activity-id"
    assert caught.value.failure_kind == "http_error"
    assert caught.value.status_code == 429


@pytest.mark.asyncio
async def test_post_submission_response_error_retains_activity() -> None:
    client = FakeHeatmapClient(status_error=FortyGuardResponseError("fake secret"))

    with pytest.raises(FortyGuardStatusRequestError) as caught:
        await create_heatmap(client, {}, sleep=no_sleep)

    assert caught.value.activity_id == "returned-activity-id"
    assert caught.value.failure_kind == "response_error"
    assert caught.value.status_code is None
    assert "fake secret" not in str(caught.value)


@pytest.mark.asyncio
async def test_service_timeout_retains_submitted_activity_id() -> None:
    processing = ActivityStatus(activity_id="returned-activity-id", status="Processing")
    client = FakeHeatmapClient([processing, processing])

    with pytest.raises(FortyGuardPollingTimeout) as caught:
        await create_heatmap(client, {}, delays=(0,), sleep=no_sleep)

    assert caught.value.activity_id == "returned-activity-id"


@pytest.mark.asyncio
async def test_pre_submission_http_failure_has_no_activity_context() -> None:
    client = FakeHeatmapClient(submit_error=FortyGuardHTTPError(500))

    with pytest.raises(FortyGuardHTTPError) as caught:
        await create_heatmap(client, {}, sleep=no_sleep)

    assert caught.value.status_code == 500
    assert not hasattr(caught.value, "activity_id")
    assert client.polled_activity_ids == []
