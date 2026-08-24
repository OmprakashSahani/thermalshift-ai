from dataclasses import replace

import pytest

from thermalshift.benchmark.comparison import compare_metrics, format_headline
from thermalshift.benchmark.models import BenchmarkMetrics


def metrics(
    name: str,
    *,
    ids: tuple[str, ...] = ("a", "b"),
    exposure: float = 10,
    deadline_rate: float | None = None,
    total: int = 2,
) -> BenchmarkMetrics:
    scheduled = len(ids)
    if deadline_rate is None:
        deadline_rate = scheduled / total
    return BenchmarkMetrics(
        scheduler_name=name,
        total_workloads=total,
        scheduled_count=scheduled,
        unscheduled_count=total - scheduled,
        completion_rate=scheduled / total,
        deadline_satisfied_count=round(deadline_rate * total),
        deadline_satisfaction_rate=deadline_rate,
        scheduled_workload_ids=ids,
        unscheduled_workload_ids=tuple(
            chr(ord("a") + i)
            for i in range(total)
            if chr(ord("a") + i) not in ids
        ),
        total_scheduled_workload_hours=float(scheduled),
        total_thermal_exposure_stress_hours=exposure,
        mean_thermal_exposure_per_scheduled_workload=exposure / scheduled if scheduled else 0,
        mean_occupied_thermal_stress=exposure / scheduled if scheduled else 0,
        peak_occupied_thermal_stress=min(exposure, 1),
        runtime_ms=0,
    )


def test_positive_and_negative_reductions_are_not_clamped() -> None:
    baseline = metrics("first_available", exposure=10)
    better = compare_metrics(baseline, metrics("thermalshift", exposure=7))
    worse = compare_metrics(baseline, metrics("thermalshift", exposure=12))
    assert better.thermal_exposure_reduction_pct == pytest.approx(30)
    assert better.thermal_exposure_delta_stress_hours == -3
    assert worse.thermal_exposure_reduction_pct == pytest.approx(-20)


def test_zero_baseline_has_no_percentage() -> None:
    comparison = compare_metrics(
        metrics("baseline", exposure=0), metrics("thermalshift", exposure=0)
    )
    assert comparison.direct_thermal_comparison_valid
    assert comparison.thermal_exposure_reduction_pct is None


def test_critical_fairness_case_blocks_claim() -> None:
    baseline = metrics("first_available", ids=("a", "b"), exposure=10)
    candidate = metrics("thermalshift", ids=("a",), exposure=1)
    comparison = compare_metrics(baseline, candidate)
    assert not comparison.same_scheduled_workload_set
    assert not comparison.direct_thermal_comparison_valid
    assert comparison.thermal_exposure_reduction_pct is None
    assert "reduced" not in format_headline(comparison)


def test_preservation_logic_and_headline_gates() -> None:
    baseline = metrics("first_available", exposure=10, deadline_rate=0.5)
    valid = compare_metrics(baseline, metrics("thermalshift", exposure=8, deadline_rate=1))
    assert valid.completion_preserved
    assert valid.deadline_satisfaction_preserved
    assert "modeled ambient thermal exposure by 20.0%" in format_headline(valid)
    assert "100.0% deadline satisfaction" in format_headline(valid)

    no_completion = compare_metrics(
        metrics("baseline", ids=("a",), exposure=5, total=2),
        metrics("thermalshift", ids=(), exposure=0, deadline_rate=0, total=2),
    )
    assert not no_completion.completion_preserved
    assert "reduced modeled" not in format_headline(no_completion)

    no_deadline = compare_metrics(
        metrics("baseline", exposure=10), metrics("thermalshift", exposure=8, deadline_rate=0.5)
    )
    assert not no_deadline.deadline_satisfaction_preserved
    assert "preserve deadline satisfaction" in format_headline(no_deadline)

    worse = replace(valid, thermal_exposure_reduction_pct=-2)
    assert "reduced modeled" not in format_headline(worse)
    assert "2.0% higher modeled thermal exposure" in format_headline(worse)
