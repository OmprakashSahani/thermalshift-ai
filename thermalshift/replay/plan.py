"""Predeclared historical windows and deterministic cache-only plans."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from thermalshift.domain.sites import get_default_sites
from thermalshift.fortyguard.cache import HeatmapResultCache, cache_key_for_payload
from thermalshift.fortyguard.payloads import build_historical_heatmap_payload

from .models import HistoricalReplayWindow, ReplayCollectionPlan, ReplayPlanEntry

SUMMER_WINDOW = HistoricalReplayWindow(
    window_id="summer-midday-v1",
    description=(
        "Six-hour replay extending the predeclared midsummer calibration anchor."
    ),
    start_utc=datetime(2024, 7, 15, 18, tzinfo=UTC),
    slot_count=6,
)
WINTER_WINDOW = HistoricalReplayWindow(
    window_id="winter-overnight-v1",
    description=(
        "Contrasting six-hour validation replay extending the predeclared winter anchor."
    ),
    start_utc=datetime(2024, 1, 15, 6, tzinfo=UTC),
    slot_count=6,
)
PREDECLARED_WINDOWS = (SUMMER_WINDOW, WINTER_WINDOW)

# This is the original site-major 4 x 7 calibration schedule. Its instants are
# deliberately independent of newly collected replay outcomes.
CALIBRATION_INSTANTS = (
    datetime(2024, 1, 15, 6, tzinfo=UTC),
    datetime(2024, 3, 20, 15, tzinfo=UTC),
    datetime(2024, 6, 1, 21, tzinfo=UTC),
    datetime(2024, 7, 15, 18, tzinfo=UTC),
    datetime(2024, 8, 31, 3, tzinfo=UTC),
    datetime(2024, 10, 15, 12, tzinfo=UTC),
    datetime(2024, 12, 15, 23, tzinfo=UTC),
)


def get_replay_window(window_id: str) -> HistoricalReplayWindow:
    """Return a predeclared replay window by stable ID."""
    try:
        return next(window for window in PREDECLARED_WINDOWS if window.window_id == window_id)
    except StopIteration as exc:
        raise ValueError(f"unknown replay window: {window_id}") from exc


def build_replay_plan(
    window: HistoricalReplayWindow,
    cache: HeatmapResultCache | None = None,
) -> ReplayCollectionPlan:
    """Build a deterministic hour-major four-site cache plan without network access."""
    result_cache = cache or HeatmapResultCache()
    entries: list[ReplayPlanEntry] = []
    for timestamp in window.instants:
        for site in get_default_sites():
            entries.append(
                _entry(
                    len(entries) + 1,
                    window.window_id,
                    site,
                    timestamp,
                    result_cache,
                )
            )
    return ReplayCollectionPlan(window=window, entries=tuple(entries))


def build_calibration_plan(
    cache: HeatmapResultCache | None = None,
) -> tuple[ReplayPlanEntry, ...]:
    """Reconstruct the original site-major 28-request calibration plan."""
    result_cache = cache or HeatmapResultCache()
    entries: list[ReplayPlanEntry] = []
    for site in get_default_sites():
        for timestamp in CALIBRATION_INSTANTS:
            entries.append(
                _entry(
                    len(entries) + 1,
                    "original-calibration-4x7",
                    site,
                    timestamp,
                    result_cache,
                )
            )
    return tuple(entries)


def _entry(request_number, window_id, site, timestamp, cache):
    payload = build_historical_heatmap_payload(site, timestamp)
    return ReplayPlanEntry(
        request_number=request_number,
        window_id=window_id,
        site_id=site.site_id,
        requested_utc=timestamp,
        site_local_time=timestamp.astimezone(ZoneInfo(site.timezone)),
        cache_key=cache_key_for_payload(payload),
        cache_hit=cache.contains(payload),
    )
