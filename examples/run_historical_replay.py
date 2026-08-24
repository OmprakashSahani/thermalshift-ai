"""Run a FortyGuard-backed historical replay entirely from local cache."""

import argparse

from thermalshift.benchmark.comparison import format_headline, thermalshift_comparisons
from thermalshift.benchmark.runner import run_benchmark
from thermalshift.fortyguard.cache import HeatmapResultCache
from thermalshift.replay.adapter import (
    build_historical_replay_scenario,
    load_calibration_status,
)
from thermalshift.replay.plan import build_replay_plan, get_replay_window


def main(argv: list[str] | None = None, cache: HeatmapResultCache | None = None) -> int:
    """Run only when both fixed calibration and replay cache inputs are complete."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--window",
        choices=("summer-midday-v1", "winter-overnight-v1"),
        default="summer-midday-v1",
    )
    args = parser.parse_args(argv)
    result_cache = cache or HeatmapResultCache()
    window = get_replay_window(args.window)
    calibration = load_calibration_status(result_cache)
    replay_plan = build_replay_plan(window, result_cache)

    if not calibration.official_ready or replay_plan.missing_count:
        print("INCOMPLETE — NO BENCHMARK WAS RUN")
        print(
            "Calibration cache: "
            f"{calibration.available_count}/{calibration.expected_count} "
            f"({calibration.expected_count - calibration.available_count} missing)"
        )
        print(
            f"Replay cache: {replay_plan.cache_hit_count}/{len(replay_plan.entries)} "
            f"({replay_plan.missing_count} missing)"
        )
        if calibration.reference_error:
            print(f"Calibration reference error: {calibration.reference_error}")
        print("Synthetic replacement and interpolation are disabled.")
        return 1

    scenario = build_historical_replay_scenario(window, result_cache)
    report = run_benchmark(scenario)
    print("FORTYGUARD-BACKED HISTORICAL REPLAY")
    print("REAL HISTORICAL AMBIENT TEMPERATURES + MODELED WORKLOADS")
    print(
        "Scheduler        Scheduled  Total  Completion %  Deadline %  "
        "Stress-hours  Mean occupied  Peak occupied  Runtime ms"
    )
    for run in report.runs:
        item = run.metrics
        print(
            f"{item.scheduler_name:<16} {item.scheduled_count:<10} "
            f"{item.total_workloads:<6} {100 * item.completion_rate:<13.1f} "
            f"{100 * item.deadline_satisfaction_rate:<11.1f} "
            f"{item.total_thermal_exposure_stress_hours:<13.3f} "
            f"{item.mean_occupied_thermal_stress:<14.3f} "
            f"{item.peak_occupied_thermal_stress:<13.3f} {item.runtime_ms:.3f}"
        )
    for comparison in thermalshift_comparisons(report):
        baseline = comparison.baseline_scheduler.replace("_", " ").title()
        print(f"\nThermalShift vs {baseline}:")
        print(f"  completion preserved: {comparison.completion_preserved}")
        print(
            "  deadline satisfaction preserved: "
            f"{comparison.deadline_satisfaction_preserved}"
        )
        print(f"  direct comparison valid: {comparison.direct_thermal_comparison_valid}")
        print(f"  {format_headline(comparison)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
