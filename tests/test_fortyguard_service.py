"""Tests for the FortyGuard heatmap service composition."""

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.test_fortyguard_models import completed_data
from thermalshift.fortyguard.models import ActivityStatus, HeatmapResult
from thermalshift.fortyguard.service import create_heatmap


class FakeHeatmapClient:
    def __init__(self, statuses: Sequence[ActivityStatus]) -> None:
        self._statuses = iter(statuses)
        self.submissions: list[Mapping[str, Any]] = []
        self.polled_activity_ids: list[str] = []

    async def submit_heatmap(self, payload: Mapping[str, Any]) -> str:
        self.submissions.append(payload)
        return "returned-activity-id"

    async def get_status(self, activity_id: str) -> ActivityStatus:
        self.polled_activity_ids.append(activity_id)
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
