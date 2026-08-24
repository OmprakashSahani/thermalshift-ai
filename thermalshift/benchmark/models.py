"""Immutable models for reproducible scheduler benchmarks."""

from collections.abc import Iterable
from dataclasses import dataclass

from thermalshift.domain.models import Site, Workload
from thermalshift.scheduler.grid import ThermalGrid
from thermalshift.scheduler.models import SchedulingResult


@dataclass(frozen=True, slots=True)
class BenchmarkScenario:
    """One controlled set of inputs shared by every compared scheduler."""

    scenario_id: str
    description: str
    sites: tuple[Site, ...]
    workloads: tuple[Workload, ...]
    thermal_grid: ThermalGrid
    data_source_label: str

    def __post_init__(self) -> None:
        for field_name in ("scenario_id", "description", "data_source_label"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} must not be blank")
        if not self.sites:
            raise ValueError("benchmark scenario must contain at least one site")
        if not self.workloads:
            raise ValueError("benchmark scenario must contain at least one workload")
        _require_unique((site.site_id for site in self.sites), "site")
        _require_unique((workload.workload_id for workload in self.workloads), "workload")
        if not self.thermal_grid.available_timestamps():
            raise ValueError("benchmark scenario thermal grid must not be empty")


@dataclass(frozen=True, slots=True)
class BenchmarkMetrics:
    """Aggregate scheduling and modeled-thermal measurements for one policy."""

    scheduler_name: str
    total_workloads: int
    scheduled_count: int
    unscheduled_count: int
    completion_rate: float
    deadline_satisfied_count: int
    deadline_satisfaction_rate: float
    scheduled_workload_ids: tuple[str, ...]
    unscheduled_workload_ids: tuple[str, ...]
    total_scheduled_workload_hours: float
    total_thermal_exposure_stress_hours: float
    mean_thermal_exposure_per_scheduled_workload: float
    mean_occupied_thermal_stress: float
    peak_occupied_thermal_stress: float
    runtime_ms: float

    def __post_init__(self) -> None:
        if self.total_workloads != self.scheduled_count + self.unscheduled_count:
            raise ValueError("scheduled and unscheduled counts must equal total workloads")
        if self.scheduled_count != len(self.scheduled_workload_ids):
            raise ValueError("scheduled count must match scheduled workload IDs")
        if self.unscheduled_count != len(self.unscheduled_workload_ids):
            raise ValueError("unscheduled count must match unscheduled workload IDs")
        if set(self.scheduled_workload_ids) & set(self.unscheduled_workload_ids):
            raise ValueError("scheduled and unscheduled workload IDs must be disjoint")
        if not 0 <= self.deadline_satisfied_count <= self.scheduled_count:
            raise ValueError("deadline-satisfied count must be within scheduled count")
        if self.runtime_ms < 0:
            raise ValueError("runtime_ms must not be negative")


@dataclass(frozen=True, slots=True)
class BenchmarkRun:
    """A scheduler's raw result and its derived metrics."""

    result: SchedulingResult
    metrics: BenchmarkMetrics

    def __post_init__(self) -> None:
        if self.result.scheduler_name != self.metrics.scheduler_name:
            raise ValueError("result and metrics scheduler names must match")


@dataclass(frozen=True, slots=True)
class BenchmarkReport:
    """Ordered results for all policies evaluated on one scenario."""

    scenario_id: str
    description: str
    data_source_label: str
    runs: tuple[BenchmarkRun, ...]

    def __post_init__(self) -> None:
        names = tuple(run.metrics.scheduler_name for run in self.runs)
        if len(names) != len(set(names)):
            raise ValueError("benchmark report scheduler names must be unique")

    def run_for(self, scheduler_name: str) -> BenchmarkRun:
        """Return the run for a scheduler name."""
        return next(run for run in self.runs if run.metrics.scheduler_name == scheduler_name)


def _require_unique(values: Iterable[str], entity: str) -> None:
    materialized = tuple(values)
    if len(materialized) != len(set(materialized)):
        raise ValueError(f"benchmark scenario {entity} IDs must be unique")
