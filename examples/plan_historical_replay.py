"""Print a deterministic cache-only historical replay collection plan."""

import argparse

from thermalshift.fortyguard.cache import HeatmapResultCache
from thermalshift.replay.adapter import load_calibration_status
from thermalshift.replay.plan import build_replay_plan, get_replay_window


def main(argv: list[str] | None = None, cache: HeatmapResultCache | None = None) -> int:
    """Print replay and calibration cache readiness without submitting requests."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--window",
        choices=("summer-midday-v1", "winter-overnight-v1"),
        default="summer-midday-v1",
    )
    args = parser.parse_args(argv)
    result_cache = cache or HeatmapResultCache()
    window = get_replay_window(args.window)
    plan = build_replay_plan(window, result_cache)
    calibration = load_calibration_status(result_cache)

    print("DRY RUN — NO REQUESTS WERE SUBMITTED")
    print(f"Replay window: {window.window_id}")
    print("Hourly UTC instants:")
    for instant in window.instants:
        print(f"  {instant.isoformat().replace('+00:00', 'Z')}")
    print("\nReplay entries (hour-major):")
    for entry in plan.entries:
        state = "CACHE HIT" if entry.cache_hit else "MISSING"
        print(
            f"{entry.request_number:02d} {entry.site_id} "
            f"requested_utc={entry.requested_utc.isoformat()} "
            f"site_local={entry.site_local_time.isoformat()} "
            f"cache_key={entry.cache_key} {state}"
        )
    print(f"\nTotal planned entries: {len(plan.entries)}")
    print(f"Existing replay cache hits: {plan.cache_hit_count}")
    print(f"New API calls needed: {plan.missing_count}")
    print(
        "Calibration cache completeness: "
        f"{calibration.available_count}/{calibration.expected_count}"
    )
    print(f"Replay cache completeness: {plan.cache_hit_count}/{len(plan.entries)}")
    if calibration.diagnostics is not None and not calibration.complete:
        print(
            "PROVISIONAL pooled P10/P90: "
            f"{calibration.diagnostics.p10_c:.3f} C / "
            f"{calibration.diagnostics.p90_c:.3f} C"
        )
    print("DRY RUN COMPLETE — NO REQUESTS WERE SUBMITTED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
