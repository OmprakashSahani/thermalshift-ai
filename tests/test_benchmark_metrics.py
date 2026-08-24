from datetime import UTC, datetime, timedelta

import pytest

from thermalshift.benchmark.metrics import calculate_metrics
from thermalshift.domain.models import ScheduleDecision, Workload, WorkloadPriority
from thermalshift.scheduler.grid import ThermalGrid, ThermalGridEntry
from thermalshift.scheduler.models import SchedulingResult

START = datetime(2026, 1, 1, tzinfo=UTC)


def workload(workload_id: str, duration: int = 1) -> Workload:
    return Workload(
        workload_id=workload_id,
        name=workload_id,
        gpu_demand=1,
        duration_hours=duration,
        release_time=START,
        deadline=START + timedelta(hours=4),
        priority=WorkloadPriority.MEDIUM,
        eligible_site_ids=frozenset({"site"}),
    )


def decision(workload_id: str, duration: int, exposure: float, deadline: bool = True):
    return ScheduleDecision(
        workload_id=workload_id,
        site_id="site",
        start_time=START,
        end_time=START + timedelta(hours=duration),
        thermal_exposure=exposure,
        thermal_stress_avg=exposure / duration,
        deadline_satisfied=deadline,
        capacity_satisfied=True,
        scheduler_name="test",
    )


def test_metrics_use_all_workloads_and_actual_occupied_slots() -> None:
    workloads = (workload("a", 2), workload("b"), workload("c"))
    grid = ThermalGrid(
        (
            ThermalGridEntry("site", START, 0.2),
            ThermalGridEntry("site", START + timedelta(hours=1), 0.8),
        )
    )
    result = SchedulingResult("test", (decision("a", 2, 1.0),), ("b", "c"))

    metrics = calculate_metrics(result, workloads, grid, runtime_ms=1.25)

    assert (metrics.scheduled_count, metrics.unscheduled_count) == (1, 2)
    assert metrics.completion_rate == pytest.approx(1 / 3)
    assert metrics.deadline_satisfaction_rate == pytest.approx(1 / 3)
    assert metrics.total_thermal_exposure_stress_hours == 1.0
    assert metrics.mean_thermal_exposure_per_scheduled_workload == 1.0
    assert metrics.total_scheduled_workload_hours == 2.0
    assert metrics.mean_occupied_thermal_stress == 0.5
    assert metrics.peak_occupied_thermal_stress == 0.8
    assert metrics.scheduled_workload_ids == ("a",)
    assert metrics.unscheduled_workload_ids == ("b", "c")
    assert metrics.runtime_ms == 1.25


def test_zero_scheduled_workloads_produce_sensible_zeros() -> None:
    workloads = (workload("a"), workload("b"))
    result = SchedulingResult("test", (), ("a", "b"))
    grid = ThermalGrid((ThermalGridEntry("site", START, 1),))
    metrics = calculate_metrics(result, workloads, grid, 0)

    assert metrics.completion_rate == 0
    assert metrics.deadline_satisfaction_rate == 0
    assert metrics.total_thermal_exposure_stress_hours == 0
    assert metrics.mean_thermal_exposure_per_scheduled_workload == 0
    assert metrics.total_scheduled_workload_hours == 0
    assert metrics.mean_occupied_thermal_stress == 0
    assert metrics.peak_occupied_thermal_stress == 0


def test_unscheduled_workload_cannot_contribute_or_disappear() -> None:
    workloads = (workload("a"), workload("b"))
    result = SchedulingResult("test", (decision("a", 1, 0.2),), ("b",))
    grid = ThermalGrid((ThermalGridEntry("site", START, 0.2),))
    assert calculate_metrics(result, workloads, grid, 0).total_thermal_exposure_stress_hours == 0.2

    with pytest.raises(ValueError, match="account for every"):
        calculate_metrics(SchedulingResult("test", (), ("a",)), workloads, grid, 0)
