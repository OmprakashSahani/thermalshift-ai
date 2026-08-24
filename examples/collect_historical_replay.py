"""Safely plan or explicitly collect one predeclared replay window."""

import argparse
import asyncio
import sys
from collections.abc import Awaitable, Callable, Sequence

from thermalshift.config import get_settings
from thermalshift.fortyguard.cache import HeatmapResultCache
from thermalshift.fortyguard.client import FortyGuardClient
from thermalshift.fortyguard.historical import HistoricalTemperatureService
from thermalshift.replay.adapter import load_calibration_status
from thermalshift.replay.collection import execute_replay_collection
from thermalshift.replay.models import HistoricalReplayWindow
from thermalshift.replay.plan import (
    PREDECLARED_WINDOWS,
    build_replay_plan,
    get_replay_window,
)

CONFIRMATION_VALUE = "COLLECT_FORTYGUARD_REPLAY"
DEFAULT_MAX_API_CALLS = 4
DEFAULT_WINDOW_ID = "summer-midday-v1"
SubmitRunner = Callable[[HistoricalReplayWindow, int], Awaitable[int]]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse bounded replay collection arguments."""
    raw_args = list(argv) if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--window",
        choices=tuple(window.window_id for window in PREDECLARED_WINDOWS),
        default=DEFAULT_WINDOW_ID,
    )
    parser.add_argument("--submit", action="store_true", help="enable bounded collection")
    parser.add_argument("--confirm", help=f"required exact value: {CONFIRMATION_VALUE}")
    parser.add_argument(
        "--max-api-calls",
        type=_positive_integer,
        default=DEFAULT_MAX_API_CALLS,
        metavar="N",
        help="maximum new submissions; cache hits do not count (default: 4)",
    )
    args = parser.parse_args(raw_args)
    args.max_api_calls_explicit = "--max-api-calls" in raw_args
    return args


async def run_real_collection(
    window: HistoricalReplayWindow, max_api_calls: int
) -> int:
    """Construct network dependencies only after every CLI safety gate passes."""
    settings = get_settings()
    api_key = settings.require_fortyguard_api_key()
    cache = HeatmapResultCache()
    async with FortyGuardClient(api_key, base_url=settings.fortyguard_base_url) as client:
        service = HistoricalTemperatureService(client, cache)
        summary = await execute_replay_collection(
            window, service, cache, max_api_calls=max_api_calls
        )
    return 1 if summary.failed else 0


def main(
    argv: Sequence[str] | None = None,
    *,
    submit_runner: SubmitRunner = run_real_collection,
    cache: HeatmapResultCache | None = None,
) -> int:
    """Print a dry run or pass explicit gates for bounded replay collection."""
    args = parse_args(argv)
    window = get_replay_window(args.window)
    if not args.submit:
        _print_dry_run(window, cache or HeatmapResultCache())
        return 0
    if args.confirm != CONFIRMATION_VALUE:
        print(
            "Submission blocked: pass "
            f"--confirm {CONFIRMATION_VALUE} with --submit. "
            "No API requests were made."
        )
        return 2
    if not args.max_api_calls_explicit:
        print(
            "Submission blocked: pass an explicit positive --max-api-calls N "
            "with --submit. No API requests were made."
        )
        return 2
    try:
        return asyncio.run(submit_runner(window, args.max_api_calls))
    except (RuntimeError, ValueError):
        print("Replay collection could not complete safely; no credentials were displayed.")
        return 1


def _print_dry_run(
    window: HistoricalReplayWindow, cache: HeatmapResultCache
) -> None:
    plan = build_replay_plan(window, cache)
    calibration = load_calibration_status(cache)
    print("DRY RUN ONLY — ZERO FORTYGUARD REQUESTS WILL BE MADE")
    print(f"Replay window: {window.window_id}")
    for entry in plan.entries:
        state = "CACHE HIT" if entry.cache_hit else "MISSING"
        print(
            f"{entry.request_number:02d} site={entry.site_id} "
            f"utc={entry.requested_utc.isoformat()} "
            f"local={entry.site_local_time.isoformat()} "
            f"cache_key={entry.cache_key} status={state}"
        )
    print(f"Total planned entries: {len(plan.entries)}")
    print(f"Existing replay cache hits: {plan.cache_hit_count}")
    print(f"New API calls needed: {plan.missing_count}")
    readiness = (
        f"Calibration readiness: {calibration.available_count}/"
        f"{calibration.expected_count}"
    )
    if calibration.official_ready:
        readiness += " — official replay calibration ready"
    print(readiness)
    print("DRY RUN COMPLETE — NO REQUESTS WERE SUBMITTED")


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
