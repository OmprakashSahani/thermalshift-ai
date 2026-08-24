"""Safe sequential collection for a predeclared historical replay window."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from thermalshift.domain.models import Site, TemperatureObservation
from thermalshift.domain.sites import get_default_sites
from thermalshift.fortyguard.cache import HeatmapResultCache
from thermalshift.fortyguard.payloads import build_historical_heatmap_payload
from thermalshift.fortyguard.poller import FortyGuardActivityFailed

from .adapter import load_calibration_status
from .models import HistoricalReplayWindow
from .plan import build_replay_plan


class ReplayObservationService(Protocol):
    """Cache-first observation operation needed by replay collection."""

    async def get_historical_temperature(
        self, site: Site, timestamp: datetime
    ) -> TemperatureObservation:
        """Return one cached or newly collected observation."""
        ...


@dataclass(frozen=True, slots=True)
class ReplayCollectionSummary:
    """Safe counters from one bounded replay collection execution."""

    window_id: str
    planned_entries: int
    cache_hits: int
    api_calls_made: int
    collected_successfully: int
    failed: int
    skipped: int
    remaining_uncached: int


async def execute_replay_collection(
    window: HistoricalReplayWindow,
    service: ReplayObservationService,
    cache: HeatmapResultCache,
    *,
    max_api_calls: int,
    output: Callable[[str], None] = print,
) -> ReplayCollectionSummary:
    """Process the existing replay plan sequentially within a new-call budget."""
    if max_api_calls <= 0:
        raise ValueError("max_api_calls must be positive")

    plan = build_replay_plan(window, cache)
    sites = {site.site_id: site for site in get_default_sites()}
    cache_hits = api_calls_made = collected = failed = skipped = 0
    stop_new_submissions = False

    for entry in plan.entries:
        site = sites[entry.site_id]
        payload = build_historical_heatmap_payload(site, entry.requested_utc)
        cached = cache.contains(payload)
        prefix = (
            f"{entry.request_number:02d} site={entry.site_id} "
            f"utc={entry.requested_utc.isoformat()}"
        )

        if not cached and (stop_new_submissions or api_calls_made >= max_api_calls):
            skipped += 1
            reason = (
                "new submissions stopped after failure"
                if stop_new_submissions
                else "API budget exhausted"
            )
            output(f"{prefix} status=SKIPPED: {reason}")
            continue

        if not cached:
            api_calls_made += 1
        try:
            observation = await service.get_historical_temperature(
                site, entry.requested_utc
            )
        except FortyGuardActivityFailed as exc:
            failed += 1
            stop_new_submissions = True
            output(f"{prefix} status=FAILED activity_id={exc.activity_id}")
            continue
        except (RuntimeError, ValueError):
            failed += 1
            stop_new_submissions = True
            output(f"{prefix} status=FAILED")
            continue

        if cached:
            cache_hits += 1
            status = "CACHE HIT"
        else:
            collected += 1
            status = "COLLECTED"
        output(
            f"{prefix} status={status} "
            f"mean_temperature_c={observation.temperature_c}"
        )

    remaining_uncached = sum(
        not cache.contains(
            build_historical_heatmap_payload(
                sites[entry.site_id], entry.requested_utc
            )
        )
        for entry in plan.entries
    )
    summary = ReplayCollectionSummary(
        window_id=window.window_id,
        planned_entries=len(plan.entries),
        cache_hits=cache_hits,
        api_calls_made=api_calls_made,
        collected_successfully=collected,
        failed=failed,
        skipped=skipped,
        remaining_uncached=remaining_uncached,
    )
    _print_summary(summary, cache, output)
    return summary


def _print_summary(
    summary: ReplayCollectionSummary,
    cache: HeatmapResultCache,
    output: Callable[[str], None],
) -> None:
    output("Replay collection summary:")
    for field_name in summary.__dataclass_fields__:
        output(f"{field_name}={getattr(summary, field_name)}")
    if summary.remaining_uncached == 0:
        output("Replay dataset status: complete")
    elif summary.failed:
        output("Replay dataset status: incomplete; new submissions stopped after failure")
    else:
        output("Replay dataset status: incomplete; API-call limit reached")

    calibration = load_calibration_status(cache)
    readiness = (
        f"Calibration readiness: {calibration.available_count}/"
        f"{calibration.expected_count}"
    )
    if calibration.official_ready:
        readiness += " — official replay calibration ready"
    output(readiness)
