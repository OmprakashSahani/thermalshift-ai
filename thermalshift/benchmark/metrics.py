"""Metric calculation for controlled ThermalShift scheduler comparisons."""

from datetime import timedelta

from thermalshift.domain.models import Workload
from thermalshift.scheduler.grid import ThermalGrid
from thermalshift.scheduler.models import SchedulingResult

from .models import BenchmarkMetrics


def calculate_metrics(
    result: SchedulingResult,
    workloads: tuple[Workload, ...],
    thermal_grid: ThermalGrid,
    runtime_ms: float,
) -> BenchmarkMetrics:
    """Calculate completion and occupied-slot thermal metrics for one result."""
    workload_by_id = {workload.workload_id: workload for workload in workloads}
    if len(workload_by_id) != len(workloads):
        raise ValueError("workload IDs must be unique")
    scheduled_ids = tuple(decision.workload_id for decision in result.decisions)
    result_ids = set(scheduled_ids) | set(result.unscheduled_workload_ids)
    if result_ids != set(workload_by_id):
        raise ValueError("scheduling result must account for every input workload exactly once")

    total_workloads = len(workloads)
    scheduled_count = len(scheduled_ids)
    deadline_count = sum(decision.deadline_satisfied for decision in result.decisions)
    total_exposure = sum(decision.thermal_exposure for decision in result.decisions)
    scheduled_hours = sum(workload_by_id[item].duration_hours for item in scheduled_ids)
    occupied_scores = tuple(
        thermal_grid.get_score(decision.site_id, decision.start_time + timedelta(hours=offset))
        for decision in result.decisions
        for offset in range(workload_by_id[decision.workload_id].duration_hours)
    )
    return BenchmarkMetrics(
        scheduler_name=result.scheduler_name,
        total_workloads=total_workloads,
        scheduled_count=scheduled_count,
        unscheduled_count=len(result.unscheduled_workload_ids),
        completion_rate=scheduled_count / total_workloads if total_workloads else 0.0,
        deadline_satisfied_count=deadline_count,
        deadline_satisfaction_rate=deadline_count / total_workloads if total_workloads else 0.0,
        scheduled_workload_ids=scheduled_ids,
        unscheduled_workload_ids=result.unscheduled_workload_ids,
        total_scheduled_workload_hours=float(scheduled_hours),
        total_thermal_exposure_stress_hours=total_exposure,
        mean_thermal_exposure_per_scheduled_workload=(
            total_exposure / scheduled_count if scheduled_count else 0.0
        ),
        mean_occupied_thermal_stress=(
            total_exposure / scheduled_hours if scheduled_hours else 0.0
        ),
        peak_occupied_thermal_stress=max(occupied_scores, default=0.0),
        runtime_ms=runtime_ms,
    )
