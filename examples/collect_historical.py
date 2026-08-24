"""Safely plan or explicitly collect the initial FortyGuard historical sample."""

import argparse
import asyncio
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from zoneinfo import ZoneInfo

from thermalshift.config import get_settings
from thermalshift.domain.models import Site, TemperatureObservation
from thermalshift.domain.sites import get_default_sites
from thermalshift.fortyguard.cache import (
    HeatmapResultCache,
    cache_key_for_payload,
)
from thermalshift.fortyguard.client import FortyGuardClient
from thermalshift.fortyguard.diagnostics import diagnose_failure
from thermalshift.fortyguard.historical import HistoricalTemperatureService
from thermalshift.fortyguard.payloads import build_historical_heatmap_payload
from thermalshift.replay.plan import CALIBRATION_INSTANTS
from thermalshift.thermal.calibration import (
    CalibrationError,
    calculate_calibration_diagnostics,
    suggest_reference_pairs,
)

CONFIRMATION_VALUE = "COLLECT_FORTYGUARD_DATA"
DEFAULT_MAX_API_CALLS = 4


@dataclass(frozen=True, slots=True)
class CollectionPlanEntry:
    """One deterministic candidate historical request."""

    site_id: str
    requested_utc: datetime
    site_local_time: datetime
    cache_key: str
    cache_hit: bool


@dataclass(frozen=True, slots=True)
class CollectionSummary:
    """Safe aggregate counters for one bounded collection run."""

    planned_entries: int
    cache_hits: int
    api_calls_made: int
    collected_successfully: int
    failed: int
    skipped: int
    remaining_uncached: int


class ObservationService(Protocol):
    """Operation required by bounded collection execution."""

    async def get_historical_temperature(
        self, site: Site, timestamp: datetime
    ) -> TemperatureObservation:
        """Return one cached or newly collected observation."""
        ...


def get_calibration_instants() -> tuple[datetime, ...]:
    """Return seven seasonally and diurnally varied UTC instants in 2024."""
    return CALIBRATION_INSTANTS


def build_collection_plan(
    cache: HeatmapResultCache | None = None,
) -> tuple[CollectionPlanEntry, ...]:
    """Build the underlying site-major four-by-seven collection plan."""
    result_cache = cache or HeatmapResultCache()
    entries: list[CollectionPlanEntry] = []
    for site in get_default_sites():
        for timestamp in get_calibration_instants():
            payload = build_historical_heatmap_payload(site, timestamp)
            entries.append(
                CollectionPlanEntry(
                    site_id=site.site_id,
                    requested_utc=timestamp,
                    site_local_time=timestamp.astimezone(ZoneInfo(site.timezone)),
                    cache_key=cache_key_for_payload(payload),
                    cache_hit=result_cache.contains(payload),
                )
            )
    return tuple(entries)


def get_submission_order(
    entries: Sequence[CollectionPlanEntry],
) -> tuple[CollectionPlanEntry, ...]:
    """Put each site's first uncached entry before any second new submission."""
    preflight: list[CollectionPlanEntry] = []
    for site in get_default_sites():
        first_uncached = next(
            (entry for entry in entries if entry.site_id == site.site_id and not entry.cache_hit),
            None,
        )
        if first_uncached is not None:
            preflight.append(first_uncached)
    preflight_keys = {(entry.site_id, entry.requested_utc) for entry in preflight}
    remaining = [
        entry for entry in entries if (entry.site_id, entry.requested_utc) not in preflight_keys
    ]
    return (*preflight, *remaining)


async def execute_collection(
    service: ObservationService,
    cache: HeatmapResultCache,
    *,
    max_api_calls: int,
    output: Callable[[str], None] = print,
) -> CollectionSummary:
    """Execute the cache-first plan sequentially within a new-call budget."""
    if max_api_calls <= 0:
        raise ValueError("max_api_calls must be positive")

    plan = build_collection_plan(cache)
    ordered_entries = get_submission_order(plan)
    sites = {site.site_id: site for site in get_default_sites()}
    cache_hits = api_calls_made = collected = failed = skipped = 0
    stop_new_submissions = False
    observations: list[TemperatureObservation] = []

    for request_number, entry in enumerate(ordered_entries, start=1):
        site = sites[entry.site_id]
        payload = build_historical_heatmap_payload(site, entry.requested_utc)
        cached = cache.contains(payload)
        prefix = f"{request_number:02d} site={entry.site_id} utc={entry.requested_utc.isoformat()}"

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
            observation = await service.get_historical_temperature(site, entry.requested_utc)
        except (RuntimeError, ValueError) as exc:
            failed += 1
            stop_new_submissions = True
            diagnostic = diagnose_failure(exc)
            output(f"{prefix} status=FAILED {diagnostic.output_fields()}")
            continue

        observations.append(observation)
        if cached:
            cache_hits += 1
            status = "CACHE HIT"
        else:
            collected += 1
            status = "COLLECTED"
        output(f"{prefix} status={status} mean_temperature_c={observation.temperature_c}")

    remaining_uncached = sum(
        not cache.contains(
            build_historical_heatmap_payload(sites[entry.site_id], entry.requested_utc)
        )
        for entry in plan
    )
    summary = CollectionSummary(
        planned_entries=len(plan),
        cache_hits=cache_hits,
        api_calls_made=api_calls_made,
        collected_successfully=collected,
        failed=failed,
        skipped=skipped,
        remaining_uncached=remaining_uncached,
    )
    _print_summary(summary, observations, output)
    return summary


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse safe collection command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submit", action="store_true", help="enable bounded real collection")
    parser.add_argument("--confirm", help=f"required exact value: {CONFIRMATION_VALUE}")
    parser.add_argument(
        "--max-api-calls",
        type=_positive_integer,
        default=DEFAULT_MAX_API_CALLS,
        metavar="N",
        help="maximum new submissions; cache hits do not count (default: 4)",
    )
    return parser.parse_args(argv)


async def run_real_collection(max_api_calls: int) -> int:
    """Construct real dependencies only after all command-line safety gates pass."""
    settings = get_settings()
    api_key = settings.require_fortyguard_api_key()
    cache = HeatmapResultCache()
    async with FortyGuardClient(api_key, base_url=settings.fortyguard_base_url) as client:
        service = HistoricalTemperatureService(client, cache)
        summary = await execute_collection(service, cache, max_api_calls=max_api_calls)
    return 1 if summary.failed else 0


def main(
    argv: Sequence[str] | None = None,
    *,
    submit_runner: Callable[[int], Awaitable[int]] = run_real_collection,
) -> int:
    """Print a dry-run plan or pass explicit gates for bounded collection."""
    args = parse_args(argv)
    if not args.submit:
        _print_dry_run()
        return 0
    if args.confirm != CONFIRMATION_VALUE:
        print(
            "Submission blocked: pass "
            f"--confirm {CONFIRMATION_VALUE} with --submit. No API requests were made."
        )
        return 2
    try:
        return asyncio.run(submit_runner(args.max_api_calls))
    except (RuntimeError, ValueError):
        print("Collection could not start or complete safely; no credentials were displayed.")
        return 1


def _print_dry_run() -> None:
    entries = build_collection_plan()
    print("DRY RUN ONLY: no FortyGuard API requests will be made.")
    print("Initial calibration sample (not a complete climatic baseline):")
    for request_number, entry in enumerate(entries, start=1):
        print(
            f"{request_number:02d} site={entry.site_id} "
            f"utc={entry.requested_utc.isoformat()} "
            f"local={entry.site_local_time.isoformat()} cache_key={entry.cache_key}"
        )
    print(f"Total planned requests: {len(entries)}")
    print(f"Existing cache hits: {sum(entry.cache_hit for entry in entries)}")


def _print_summary(
    summary: CollectionSummary,
    observations: Sequence[TemperatureObservation],
    output: Callable[[str], None],
) -> None:
    output("Collection summary:")
    for field_name in summary.__dataclass_fields__:
        output(f"{field_name}={getattr(summary, field_name)}")
    if summary.remaining_uncached == 0:
        output("Dataset status: complete")
    elif summary.failed:
        output("Dataset status: incomplete; new submissions stopped after failure")
    else:
        output("Dataset status: incomplete; API-call limit reached")

    if len(observations) < 2:
        output("Calibration diagnostics are premature: fewer than two observations available.")
        return
    diagnostics = calculate_calibration_diagnostics(observations)
    output(
        "Pooled calibration diagnostics: "
        f"count={diagnostics.count} min_c={diagnostics.minimum_c} "
        f"max_c={diagnostics.maximum_c} mean_c={diagnostics.mean_c} "
        f"median_c={diagnostics.median_c}"
    )
    try:
        pairs = suggest_reference_pairs(diagnostics)
    except CalibrationError:
        output("Candidate reference pairs unavailable: pooled values do not span a valid range.")
        return
    for pair in pairs:
        output(
            f"Candidate {pair.label}: lower_c={pair.lower_reference_c} "
            f"upper_c={pair.upper_reference_c} (diagnostic only)"
        )


def _positive_integer(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
