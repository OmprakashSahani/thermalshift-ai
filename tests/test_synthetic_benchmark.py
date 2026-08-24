from thermalshift.benchmark.comparison import thermalshift_comparisons
from thermalshift.benchmark.runner import run_benchmark
from thermalshift.benchmark.synthetic import create_synthetic_scenario


def test_synthetic_scenario_shape_and_real_scheduler_results() -> None:
    scenario = create_synthetic_scenario()
    assert scenario.data_source_label == "SYNTHETIC"
    assert len(scenario.sites) >= 4
    assert len(scenario.workloads) >= 8
    assert {workload.duration_hours for workload in scenario.workloads} >= {1, 2}
    assert all(
        0 <= scenario.thermal_grid.get_score(site.site_id, timestamp) <= 1
        for site in scenario.sites
        for timestamp in scenario.thermal_grid.available_timestamps(site.site_id)
    )

    report = run_benchmark(scenario)
    metrics = {run.metrics.scheduler_name: run.metrics for run in report.runs}
    scheduled_sets = {frozenset(item.scheduled_workload_ids) for item in metrics.values()}
    assert len(scheduled_sets) == 1
    assert {item.scheduled_count for item in metrics.values()} == {len(scenario.workloads)}
    assert {item.completion_rate for item in metrics.values()} == {1.0}
    assert {item.deadline_satisfaction_rate for item in metrics.values()} == {1.0}
    thermalshift_exposure = metrics["thermalshift"].total_thermal_exposure_stress_hours
    assert thermalshift_exposure < metrics["first_available"].total_thermal_exposure_stress_hours
    assert thermalshift_exposure < metrics["capacity_only"].total_thermal_exposure_stress_hours
    for comparison in thermalshift_comparisons(report):
        assert comparison.direct_thermal_comparison_valid
        assert comparison.thermal_exposure_reduction_pct is not None
        assert comparison.thermal_exposure_reduction_pct > 0


def test_synthetic_thermalshift_decisions_repeat_exactly() -> None:
    scenario = create_synthetic_scenario()
    first = run_benchmark(scenario).run_for("thermalshift").result
    second = run_benchmark(scenario).run_for("thermalshift").result
    assert first == second
