"""Run the deterministic offline ThermalShift scheduler demonstration."""

import argparse
from pathlib import Path

from thermalshift.benchmark.artifacts import (
    build_benchmark_artifact,
    write_benchmark_artifacts,
)
from thermalshift.benchmark.comparison import format_headline, thermalshift_comparisons
from thermalshift.benchmark.runner import run_benchmark
from thermalshift.benchmark.synthetic import create_synthetic_scenario


def main(argv: list[str] | None = None) -> None:
    """Print compact scheduler metrics and fairness-qualified comparisons."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    scenario = create_synthetic_scenario()
    report = (
        run_benchmark(scenario, timer=lambda: 0) if args.output_dir else run_benchmark(scenario)
    )
    print("SYNTHETIC DEMONSTRATION — NOT FORTYGUARD BENCHMARK EVIDENCE")
    headers = (
        "Scheduler",
        "Scheduled",
        "Total",
        "Completion %",
        "Deadline %",
        "Thermal stress-hours",
        "Mean occupied stress",
        "Peak occupied stress",
        "Runtime ms",
    )
    rows = [
        (
            run.metrics.scheduler_name,
            str(run.metrics.scheduled_count),
            str(run.metrics.total_workloads),
            f"{100 * run.metrics.completion_rate:.1f}",
            f"{100 * run.metrics.deadline_satisfaction_rate:.1f}",
            f"{run.metrics.total_thermal_exposure_stress_hours:.3f}",
            f"{run.metrics.mean_occupied_thermal_stress:.3f}",
            f"{run.metrics.peak_occupied_thermal_stress:.3f}",
            f"{run.metrics.runtime_ms:.3f}",
        )
        for run in report.runs
    ]
    widths = tuple(
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    )
    print("  ".join(value.ljust(widths[index]) for index, value in enumerate(headers)))
    for row in rows:
        print("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)))

    for comparison in thermalshift_comparisons(report):
        baseline = comparison.baseline_scheduler.replace("_", " ").title()
        print(f"\nThermalShift vs {baseline}:")
        print(f"  completion preserved: {comparison.completion_preserved}")
        print(f"  deadline satisfaction preserved: {comparison.deadline_satisfaction_preserved}")
        print(f"  direct comparison valid: {comparison.direct_thermal_comparison_valid}")
        if comparison.thermal_exposure_reduction_pct is None:
            print("  thermal reduction percentage: unavailable")
        else:
            print(
                f"  thermal reduction percentage: {comparison.thermal_exposure_reduction_pct:.1f}%"
            )
        print(f"  Synthetic illustration only: {format_headline(comparison)}")

    if args.output_dir:
        artifact = build_benchmark_artifact(
            scenario, report, evidence_type="synthetic_demonstration"
        )
        json_path, markdown_path = write_benchmark_artifacts(artifact, args.output_dir)
        print(f"\nWrote {json_path}")
        print(f"Wrote {markdown_path}")


if __name__ == "__main__":
    main()
