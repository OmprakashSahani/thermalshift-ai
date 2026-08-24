from dataclasses import FrozenInstanceError

import pytest

from thermalshift.benchmark.models import BenchmarkScenario
from thermalshift.benchmark.runner import run_benchmark
from thermalshift.benchmark.synthetic import create_synthetic_scenario
from thermalshift.scheduler.models import SchedulingResult


def test_runner_order_injectable_timing_and_immutable_inputs() -> None:
    scenario = create_synthetic_scenario()
    original_sites = scenario.sites
    original_workloads = scenario.workloads
    seen: list[tuple[object, object, object]] = []

    def scheduler(sites, workloads, grid):
        seen.append((sites, workloads, grid))
        return SchedulingResult("clocked", (), tuple(sorted(w.workload_id for w in workloads)))

    ticks = iter((1_000_000, 3_500_000))
    report = run_benchmark(scenario, timer=lambda: next(ticks), schedulers=(scheduler,))

    assert report.runs[0].metrics.runtime_ms == 2.5
    assert seen == [(scenario.sites, scenario.workloads, scenario.thermal_grid)]
    assert scenario.sites is original_sites
    assert scenario.workloads is original_workloads
    with pytest.raises(FrozenInstanceError):
        scenario.description = "changed"  # type: ignore[misc]


def test_default_runner_executes_expected_deterministic_order() -> None:
    report = run_benchmark(create_synthetic_scenario())
    names = tuple(run.metrics.scheduler_name for run in report.runs)
    assert names == ("first_available", "capacity_only", "thermalshift")


def test_repeated_non_runtime_outputs_are_identical() -> None:
    scenario = create_synthetic_scenario()
    first = run_benchmark(scenario)
    second = run_benchmark(scenario)
    assert tuple(run.result for run in first.runs) == tuple(run.result for run in second.runs)
    assert tuple(
        (run.metrics.scheduler_name, run.metrics.total_thermal_exposure_stress_hours)
        for run in first.runs
    ) == tuple(
        (run.metrics.scheduler_name, run.metrics.total_thermal_exposure_stress_hours)
        for run in second.runs
    )


def test_scheduler_errors_are_not_swallowed() -> None:
    def broken(_sites, _workloads, _grid):
        raise RuntimeError("scheduler failed")

    with pytest.raises(RuntimeError, match="scheduler failed"):
        run_benchmark(create_synthetic_scenario(), schedulers=(broken,))


@pytest.mark.parametrize("field", ["scenario_id", "description", "data_source_label"])
def test_scenario_requires_nonblank_metadata(field: str) -> None:
    scenario = create_synthetic_scenario()
    values = {
        "scenario_id": scenario.scenario_id,
        "description": scenario.description,
        "data_source_label": scenario.data_source_label,
    }
    values[field] = " "
    with pytest.raises(ValueError, match=field):
        BenchmarkScenario(
            **values,
            sites=scenario.sites,
            workloads=scenario.workloads,
            thermal_grid=scenario.thermal_grid,
        )
