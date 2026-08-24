"""Deterministic orchestration of the three scheduler benchmark."""

from collections.abc import Callable, Iterable
from time import perf_counter_ns

from thermalshift.domain.models import Site, Workload
from thermalshift.scheduler import (
    ThermalGrid,
    schedule_capacity_only,
    schedule_first_available,
    schedule_thermalshift,
)
from thermalshift.scheduler.models import SchedulingResult

from .metrics import calculate_metrics
from .models import BenchmarkReport, BenchmarkRun, BenchmarkScenario

Scheduler = Callable[[Iterable[Site], Iterable[Workload], ThermalGrid], SchedulingResult]
Timer = Callable[[], int]
DEFAULT_SCHEDULERS: tuple[Scheduler, ...] = (
    schedule_first_available,
    schedule_capacity_only,
    schedule_thermalshift,
)


def run_benchmark(
    scenario: BenchmarkScenario,
    *,
    timer: Timer = perf_counter_ns,
    schedulers: tuple[Scheduler, ...] = DEFAULT_SCHEDULERS,
) -> BenchmarkReport:
    """Run the fixed scheduler suite against identical immutable inputs."""
    runs: list[BenchmarkRun] = []
    for scheduler in schedulers:
        started_ns = timer()
        result = scheduler(scenario.sites, scenario.workloads, scenario.thermal_grid)
        elapsed_ms = (timer() - started_ns) / 1_000_000
        metrics = calculate_metrics(
            result, scenario.workloads, scenario.thermal_grid, elapsed_ms
        )
        runs.append(BenchmarkRun(result=result, metrics=metrics))
    return BenchmarkReport(
        scenario_id=scenario.scenario_id,
        description=scenario.description,
        data_source_label=scenario.data_source_label,
        runs=tuple(runs),
    )
