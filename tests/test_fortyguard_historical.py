"""Tests for cache-first historical temperature orchestration."""

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from tests.test_fortyguard_models import completed_data
from thermalshift.domain.sites import get_default_sites
from thermalshift.fortyguard.cache import HeatmapResultCache
from thermalshift.fortyguard.historical import HistoricalTemperatureService
from thermalshift.fortyguard.models import HeatmapResult
from thermalshift.fortyguard.payloads import build_historical_heatmap_payload


def sample_result() -> HeatmapResult:
    return HeatmapResult.model_validate(completed_data()["result"])


class CreatorRecorder:
    def __init__(self, *, failure: RuntimeError | None = None) -> None:
        self.calls: list[Mapping[str, Any]] = []
        self.options: list[dict[str, Any]] = []
        self.failure = failure

    async def __call__(
        self, client: object, payload: Mapping[str, Any], **kwargs: Any
    ) -> HeatmapResult:
        self.calls.append(payload)
        self.options.append(kwargs)
        if self.failure is not None:
            raise self.failure
        return sample_result()


@pytest.mark.asyncio
async def test_cache_miss_calls_once_caches_and_builds_raw_observation(tmp_path: Path) -> None:
    site = get_default_sites()[0]
    timestamp = datetime(2024, 7, 15, 18, tzinfo=UTC)
    cache = HeatmapResultCache(tmp_path)
    creator = CreatorRecorder()
    service = HistoricalTemperatureService(object(), cache, heatmap_creator=creator)

    observation = await service.get_historical_temperature(site, timestamp)

    payload = build_historical_heatmap_payload(site, timestamp)
    assert len(creator.calls) == 1
    assert cache.get(payload) == sample_result()
    assert observation.temperature_c == pytest.approx(36.756608333333325)
    assert observation.source == "fortyguard"
    assert observation.observation_type == "historical"
    assert observation.timestamp is timestamp
    assert creator.options[0]["poll_interval_seconds"] == 5.0
    assert creator.options[0]["max_status_checks"] == 120


@pytest.mark.asyncio
async def test_short_polling_policy_and_fake_sleep_are_injectable(tmp_path: Path) -> None:
    site = get_default_sites()[0]
    timestamp = datetime(2024, 7, 15, 18, tzinfo=UTC)
    creator = CreatorRecorder()
    service = HistoricalTemperatureService(
        object(), HeatmapResultCache(tmp_path), heatmap_creator=creator
    )

    async def fake_sleep(delay: float) -> None:
        return None

    await service.get_historical_temperature(
        site,
        timestamp,
        poll_interval_seconds=0,
        max_status_checks=1,
        sleep=fake_sleep,
    )

    assert creator.options == [
        {
            "poll_interval_seconds": 0,
            "max_status_checks": 1,
            "sleep": fake_sleep,
        }
    ]


@pytest.mark.asyncio
async def test_cache_hit_performs_zero_submissions(tmp_path: Path) -> None:
    site = get_default_sites()[0]
    timestamp = datetime(2024, 7, 15, 18, tzinfo=UTC)
    cache = HeatmapResultCache(tmp_path)
    cache.put(build_historical_heatmap_payload(site, timestamp), sample_result())
    creator = CreatorRecorder()
    service = HistoricalTemperatureService(object(), cache, heatmap_creator=creator)

    observation = await service.get_historical_temperature(site, timestamp)

    assert creator.calls == []
    assert observation.site_id == site.site_id


@pytest.mark.asyncio
async def test_failed_upstream_operation_is_not_cached(tmp_path: Path) -> None:
    site = get_default_sites()[0]
    timestamp = datetime(2024, 7, 15, 18, tzinfo=UTC)
    cache = HeatmapResultCache(tmp_path)
    creator = CreatorRecorder(failure=RuntimeError("upstream failed"))
    service = HistoricalTemperatureService(object(), cache, heatmap_creator=creator)

    with pytest.raises(RuntimeError, match="upstream failed"):
        await service.get_historical_temperature(site, timestamp)

    assert not cache.contains(build_historical_heatmap_payload(site, timestamp))
