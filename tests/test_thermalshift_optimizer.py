"""Tests for completion-first ThermalShift CP-SAT optimization."""

from datetime import timedelta

import pytest

from tests.test_first_available_scheduler import START, grid_for, site, workload
from thermalshift.scheduler.first_available import schedule as schedule_first_available
from thermalshift.scheduler.optimizer import schedule


def test_chooses_cooler_site_when_operationally_equivalent() -> None:
    result = schedule(
        [site("site-a"), site("site-b")],
        [workload("w")],
        grid_for({"site-a": [0.8], "site-b": [0.2]}),
    )

    assert result.decisions[0].site_id == "site-b"


def test_chooses_cooler_later_time_within_deadline() -> None:
    result = schedule(
        [site("site-a")],
        [workload("w", deadline_hour=2)],
        grid_for({"site-a": [0.9, 0.1]}),
    )

    assert result.decisions[0].start_time == START + timedelta(hours=1)


def test_respects_eligibility_release_and_deadline() -> None:
    result = schedule(
        [site("site-a"), site("site-b")],
        [workload("w", release_hour=1, deadline_hour=2, eligible=("site-a",))],
        grid_for({"site-a": [0.0, 0.8], "site-b": [0.0, 0.0]}),
    )

    decision = result.decisions[0]
    assert decision.site_id == "site-a"
    assert decision.start_time == START + timedelta(hours=1)
    assert decision.end_time == START + timedelta(hours=2)


def test_multi_hour_overlap_never_exceeds_capacity() -> None:
    jobs = [
        workload("a", demand=40, duration=2, deadline_hour=3, eligible=("site-a",)),
        workload("b", demand=40, duration=2, deadline_hour=3, eligible=("site-a",)),
    ]
    result = schedule(
        [site("site-a", 64)], jobs, grid_for({"site-a": [0.1, 0.1, 0.1]})
    )

    assert result.scheduled_count == 1
    assert result.unscheduled_count == 1


def test_multiple_workloads_can_run_simultaneously_when_aggregate_fits() -> None:
    jobs = [
        workload("a", demand=32, deadline_hour=1, eligible=("site-a",)),
        workload("b", demand=32, deadline_hour=1, eligible=("site-a",)),
    ]
    result = schedule([site("site-a", 64)], jobs, grid_for({"site-a": [0.4]}))

    assert result.scheduled_count == 2
    assert {decision.start_time for decision in result.decisions} == {START}


def test_infeasible_workload_is_unscheduled_and_no_candidates_is_valid() -> None:
    job = workload("w", demand=65, eligible=("site-a",))

    result = schedule([site("site-a", 64)], [job], grid_for({"site-a": [0.2]}))

    assert result.decisions == ()
    assert result.unscheduled_workload_ids == ("w",)


def test_deterministic_across_runs_and_reversed_workloads() -> None:
    jobs = [workload("b"), workload("a")]
    sites = [site("site-a"), site("site-b")]
    grid = grid_for({"site-a": [0.3, 0.3], "site-b": [0.3, 0.3]})

    first = schedule(sites, jobs, grid)
    assert first == schedule(sites, jobs, grid)
    assert first == schedule(sites, reversed(jobs), grid)


def test_correct_multi_hour_exposure_uses_grid_scores() -> None:
    result = schedule(
        [site("site-a")],
        [workload("w", duration=2, deadline_hour=2)],
        grid_for({"site-a": [0.25, 0.75]}),
    )

    decision = result.decisions[0]
    assert decision.thermal_exposure == pytest.approx(1.0)
    assert decision.thermal_stress_avg == pytest.approx(0.5)


def test_completion_is_maximized_before_thermal_exposure() -> None:
    jobs = [
        workload("a", demand=64, deadline_hour=1, eligible=("site-a",)),
        workload("b", demand=64, deadline_hour=2, eligible=("site-a",)),
    ]
    result = schedule(
        [site("site-a", 64)], jobs, grid_for({"site-a": [0.1, 0.8]})
    )

    assert result.scheduled_count == 2
    assert sum(decision.thermal_exposure for decision in result.decisions) == pytest.approx(0.9)


def test_synthetic_baseline_comparison_preserves_count_and_lowers_exposure() -> None:
    sites = [site("site-a"), site("site-b")]
    jobs = [workload("w")]
    grid = grid_for({"site-a": [0.9], "site-b": [0.1]})

    baseline = schedule_first_available(sites, jobs, grid)
    optimized = schedule(sites, jobs, grid)

    assert optimized.scheduled_count == baseline.scheduled_count == 1
    assert optimized.decisions[0].thermal_exposure < baseline.decisions[0].thermal_exposure
