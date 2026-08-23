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
        self.failure = failure

    async def __call__(
        self, client: object, payload: Mapping[str, Any], **kwargs: Any
    ) -> HeatmapResult:
        self.calls.append(payload)
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
