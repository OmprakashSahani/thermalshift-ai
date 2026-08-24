"""Fair pairwise thermal comparisons and conservative evidence wording."""

from dataclasses import dataclass

from .models import BenchmarkMetrics, BenchmarkReport


@dataclass(frozen=True, slots=True)
class PairwiseComparison:
    """Candidate deltas against a baseline with explicit comparability state."""

    baseline_scheduler: str
    candidate_scheduler: str
    scheduled_count_delta: int
    completion_rate_delta: float
    deadline_satisfaction_rate_delta: float
    candidate_deadline_satisfaction_rate: float
    completion_preserved: bool
    deadline_satisfaction_preserved: bool
    same_scheduled_workload_set: bool
    direct_thermal_comparison_valid: bool
    thermal_exposure_delta_stress_hours: float
    thermal_exposure_reduction_pct: float | None
    mean_occupied_stress_delta: float


def compare_metrics(
    baseline: BenchmarkMetrics, candidate: BenchmarkMetrics
) -> PairwiseComparison:
    """Compare metrics without presenting dropped work as a thermal improvement."""
    same_set = set(candidate.scheduled_workload_ids) == set(
        baseline.scheduled_workload_ids
    )
    exposure_delta = (
        candidate.total_thermal_exposure_stress_hours
        - baseline.total_thermal_exposure_stress_hours
    )
    reduction = None
    if same_set and baseline.total_thermal_exposure_stress_hours > 0:
        reduction = -100 * exposure_delta / baseline.total_thermal_exposure_stress_hours
    return PairwiseComparison(
        baseline_scheduler=baseline.scheduler_name,
        candidate_scheduler=candidate.scheduler_name,
        scheduled_count_delta=candidate.scheduled_count - baseline.scheduled_count,
        completion_rate_delta=candidate.completion_rate - baseline.completion_rate,
        deadline_satisfaction_rate_delta=(
            candidate.deadline_satisfaction_rate - baseline.deadline_satisfaction_rate
        ),
        candidate_deadline_satisfaction_rate=candidate.deadline_satisfaction_rate,
        completion_preserved=candidate.scheduled_count >= baseline.scheduled_count,
        deadline_satisfaction_preserved=(
            candidate.deadline_satisfaction_rate >= baseline.deadline_satisfaction_rate
        ),
        same_scheduled_workload_set=same_set,
        direct_thermal_comparison_valid=same_set,
        thermal_exposure_delta_stress_hours=exposure_delta,
        thermal_exposure_reduction_pct=reduction,
        mean_occupied_stress_delta=(
            candidate.mean_occupied_thermal_stress
            - baseline.mean_occupied_thermal_stress
        ),
    )


def thermalshift_comparisons(report: BenchmarkReport) -> tuple[PairwiseComparison, ...]:
    """Compare ThermalShift with First Available and Capacity Only, in that order."""
    candidate = report.run_for("thermalshift").metrics
    return tuple(
        compare_metrics(report.run_for(name).metrics, candidate)
        for name in ("first_available", "capacity_only")
    )


def format_headline(comparison: PairwiseComparison) -> str:
    """Return a winning claim only when all conservative evidence gates pass."""
    reduction = comparison.thermal_exposure_reduction_pct
    if (
        comparison.direct_thermal_comparison_valid
        and comparison.completion_preserved
        and comparison.deadline_satisfaction_preserved
        and reduction is not None
        and reduction > 0
    ):
        deadline_pct = 100 * comparison.candidate_deadline_satisfaction_rate
        return (
            "ThermalShift reduced modeled ambient thermal exposure by "
            f"{reduction:.1f}% versus {_display_name(comparison.baseline_scheduler)} "
            f"while preserving {deadline_pct:.1f}% deadline satisfaction."
        )
    if not comparison.direct_thermal_comparison_valid:
        return (
            "Direct thermal comparison is unavailable because the scheduled "
            "workload sets differ."
        )
    if not comparison.completion_preserved:
        return "ThermalShift did not preserve workload completion versus the baseline."
    if not comparison.deadline_satisfaction_preserved:
        return "ThermalShift did not preserve deadline satisfaction versus the baseline."
    if reduction is None:
        return "A thermal reduction percentage is unavailable because baseline exposure is zero."
    if reduction < 0:
        return (
            f"ThermalShift had {-reduction:.1f}% higher modeled thermal exposure "
            "than the baseline."
        )
    if reduction == 0:
        return "ThermalShift and the baseline had equal modeled thermal exposure."
    return (
        "ThermalShift's modeled thermal exposure reduction was "
        f"{reduction:.1f}% versus the baseline."
    )


def _display_name(value: str) -> str:
    return value.replace("_", " ").title()
