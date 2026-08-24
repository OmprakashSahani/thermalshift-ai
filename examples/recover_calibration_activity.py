"""Safely recover one completed existing activity into the calibration cache."""

import argparse
import asyncio
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from examples.collect_historical import get_calibration_instants
from thermalshift.config import get_settings
from thermalshift.domain.models import Site
from thermalshift.domain.sites import get_default_sites
from thermalshift.fortyguard.cache import HeatmapResultCache, cache_key_for_payload
from thermalshift.fortyguard.client import FortyGuardClient
from thermalshift.fortyguard.diagnostics import diagnose_failure
from thermalshift.fortyguard.models import ActivityStatus
from thermalshift.fortyguard.payloads import build_historical_heatmap_payload

CONFIRMATION_VALUE = "RECOVER_EXISTING_FORTYGUARD_CALIBRATION"


class StatusReader(Protocol):
    """One-shot status operation needed by calibration recovery."""

    async def get_status(self, activity_id: str) -> ActivityStatus:
        """Return one validated activity status."""
        ...


@dataclass(frozen=True, slots=True)
class CalibrationTarget:
    """One canonical entry in the frozen four-by-seven calibration plan."""

    site: Site
    requested_utc: datetime


def resolve_calibration_target(site_id: str, requested_utc: datetime) -> CalibrationTarget:
    """Resolve an exact canonical calibration entry or reject it before HTTP."""
    matches = [
        CalibrationTarget(site, instant)
        for site in get_default_sites()
        for instant in get_calibration_instants()
        if site.site_id == site_id and instant == requested_utc
    ]
    if len(matches) != 1:
        raise ValueError("target is not an entry in the frozen calibration plan")
    return matches[0]


async def recover_calibration_activity(
    client: StatusReader,
    cache: HeatmapResultCache,
    *,
    activity_id: str,
    target: CalibrationTarget,
    output: Callable[[str], None] = print,
) -> int:
    """Cache one validated completed activity using at most one status GET."""
    payload = build_historical_heatmap_payload(target.site, target.requested_utc)
    cache_key = cache_key_for_payload(payload)
    cached = cache.get(payload)
    if cached is not None:
        output("recovery_status=CACHE HIT")
        _print_safe_result(
            target,
            activity_id,
            cached.stats_data.temperature_stats.mean,
            cache_key,
            output,
        )
        return 0

    try:
        status = await client.get_status(activity_id)
    except (RuntimeError, ValueError) as exc:
        output(f"recovery_status=FAILED {diagnose_failure(exc).output_fields()}")
        return 1

    if status.activity_id != activity_id:
        output(
            "recovery_status=FAILED failure_kind=response_error "
            "response_reason=activity_id_mismatch"
        )
        return 1
    if status.status.casefold() != "completed":
        output(
            "recovery_status=FAILED failure_kind=response_error "
            "response_reason=activity_not_completed"
        )
        return 1
    if status.result is None:
        output(
            "recovery_status=FAILED failure_kind=response_error "
            "response_reason=completed_missing_result"
        )
        return 1

    cache.put(payload, status.result)
    output("recovery_status=CACHED")
    _print_safe_result(
        target,
        activity_id,
        status.result.stats_data.temperature_stats.mean,
        cache_key,
        output,
    )
    return 0


def _print_safe_result(
    target: CalibrationTarget,
    activity_id: str,
    mean_temperature_c: float,
    cache_key: str,
    output: Callable[[str], None],
) -> None:
    output(f"site_id={target.site.site_id}")
    output(f"requested_utc={target.requested_utc.isoformat()}")
    output(f"activity_id={activity_id}")
    output(f"mean_temperature_c={mean_temperature_c}")
    output(f"cache_key={cache_key}")
    output("request_type=GET_STATUS_ONLY")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse recovery safety gates and canonical target coordinates."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--activity-id", required=True)
    parser.add_argument("--site-id", required=True)
    parser.add_argument("--requested-utc", required=True, type=_utc_datetime)
    parser.add_argument("--confirm", required=True)
    return parser.parse_args(argv)


async def run_real_recovery(activity_id: str, target: CalibrationTarget) -> int:
    """Create real read-only dependencies after all local gates pass."""
    cache = HeatmapResultCache()
    payload = build_historical_heatmap_payload(target.site, target.requested_utc)
    if cache.contains(payload):
        return await recover_calibration_activity(
            _UnusedStatusReader(), cache, activity_id=activity_id, target=target
        )
    settings = get_settings()
    api_key = settings.require_fortyguard_api_key()
    async with FortyGuardClient(api_key, base_url=settings.fortyguard_base_url) as client:
        return await recover_calibration_activity(
            client, cache, activity_id=activity_id, target=target
        )


class _UnusedStatusReader:
    async def get_status(self, activity_id: str) -> ActivityStatus:
        raise AssertionError("cache-hit recovery must not request activity status")


def main(
    argv: Sequence[str] | None = None,
    *,
    recovery_runner: Callable[[str, CalibrationTarget], Awaitable[int]] = run_real_recovery,
) -> int:
    """Validate local safety gates before starting one-shot recovery."""
    args = parse_args(argv)
    if args.confirm != CONFIRMATION_VALUE:
        print(f"Recovery blocked: pass --confirm {CONFIRMATION_VALUE}. No API requests were made.")
        return 2
    try:
        target = resolve_calibration_target(args.site_id, args.requested_utc)
    except ValueError:
        print(
            "Recovery blocked: target is not in the frozen calibration plan. "
            "No API requests were made."
        )
        return 2
    try:
        return asyncio.run(recovery_runner(args.activity_id, target))
    except (RuntimeError, ValueError):
        print("Recovery could not start or complete safely; no credentials were displayed.")
        return 1


def _utc_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an ISO 8601 UTC timestamp") from exc
    if (
        parsed.tzinfo is None
        or parsed.utcoffset() is None
        or parsed.utcoffset().total_seconds() != 0
    ):
        raise argparse.ArgumentTypeError("must be a timezone-aware UTC timestamp")
    return parsed.astimezone(UTC)


if __name__ == "__main__":
    raise SystemExit(main())
