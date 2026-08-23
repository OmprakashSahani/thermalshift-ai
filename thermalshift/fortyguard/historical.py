"""Cache-first conversion of historical heatmaps into raw observations."""

from collections.abc import Awaitable, Callable, Iterable
from datetime import datetime

from thermalshift.domain.models import Site, TemperatureObservation
from thermalshift.fortyguard.cache import HeatmapResultCache
from thermalshift.fortyguard.models import HeatmapResult
from thermalshift.fortyguard.payloads import build_historical_heatmap_payload
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
        delays: Iterable[float] = (3.0, 6.0, 12.0),
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
            result = await self._heatmap_creator(self._client, payload, delays=delays)
            self._cache.put(payload, result)

        return TemperatureObservation(
            site_id=site.site_id,
            timestamp=timestamp,
            temperature_c=result.stats_data.temperature_stats.mean,
            source="fortyguard",
            observation_type="historical",
        )
