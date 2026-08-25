"""Cache-first conversion of historical heatmaps into raw observations."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime

from thermalshift.domain.models import Site, TemperatureObservation
from thermalshift.fortyguard.cache import HeatmapResultCache
from thermalshift.fortyguard.models import HeatmapResult
from thermalshift.fortyguard.payloads import build_historical_heatmap_payload
from thermalshift.fortyguard.poller import (
    DEFAULT_MAX_STATUS_CHECKS,
    DEFAULT_STATUS_POLL_INTERVAL_SECONDS,
)
from thermalshift.fortyguard.service import HeatmapClient, create_heatmap

HeatmapCreator = Callable[..., Awaitable[HeatmapResult]]


class HistoricalTemperatureService:
    """Obtain historical raw observations through a successful-result cache."""

    def __init__(
        self,
        client: HeatmapClient,
        cache: HeatmapResultCache,
        *,
        heatmap_creator: HeatmapCreator = create_heatmap,
    ) -> None:
        self._client = client
        self._cache = cache
        self._heatmap_creator = heatmap_creator

    async def get_historical_temperature(
        self,
        site: Site,
        timestamp: datetime,
        *,
        granularity: int = 100,
        aoi_half_size_m: float = 200.0,
        poll_interval_seconds: float = DEFAULT_STATUS_POLL_INTERVAL_SECONDS,
        max_status_checks: int = DEFAULT_MAX_STATUS_CHECKS,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> TemperatureObservation:
        """Return the cached or newly collected mean ambient temperature."""
        payload = build_historical_heatmap_payload(
            site,
            timestamp,
            granularity=granularity,
            aoi_half_size_m=aoi_half_size_m,
        )
        result = self._cache.get(payload)
        if result is None:
            result = await self._heatmap_creator(
                self._client,
                payload,
                poll_interval_seconds=poll_interval_seconds,
                max_status_checks=max_status_checks,
                sleep=sleep,
            )
            self._cache.put(payload, result)

        return TemperatureObservation(
            site_id=site.site_id,
            timestamp=timestamp,
            temperature_c=result.stats_data.temperature_stats.mean,
            source="fortyguard",
            observation_type="historical",
        )
