"""Tests for shared validation and the First Available baseline."""

from datetime import UTC, datetime, timedelta

import pytest

from thermalshift.domain.models import Site, Workload
from thermalshift.scheduler.common import SchedulingInputError
from thermalshift.scheduler.first_available import schedule
from thermalshift.scheduler.grid import ThermalGrid, ThermalGridEntry

START = datetime(2024, 1, 1, tzinfo=UTC)


def site(site_id: str, capacity: int = 8) -> Site:
    return Site(
        site_id=site_id,
        name=f"Modeled {site_id}",
        latitude=30,
        longitude=-90,
        timezone="UTC",
        total_gpu_capacity=capacity,
    )


def workload(
    workload_id: str,
    *,
    demand: int = 4,
    duration: int = 1,
    release_hour: int = 0,
    deadline_hour: int = 3,
    eligible: tuple[str, ...] = ("site-a", "site-b"),
) -> Workload:
    return Workload(
        workload_id=workload_id,
        name=workload_id,
        gpu_demand=demand,
        duration_hours=duration,
        release_time=START + timedelta(hours=release_hour),
        deadline=START + timedelta(hours=deadline_hour),
        priority="medium",
        eligible_site_ids=eligible,
    )


def grid_for(scores: dict[str, list[float]]) -> ThermalGrid:
    return ThermalGrid(
        ThermalGridEntry(site_id, START + timedelta(hours=hour), score)
        for site_id, site_scores in scores.items()
        for hour, score in enumerate(site_scores)
    )


def placement(result: object, workload_id: str):
    return next(decision for decision in result.decisions if decision.workload_id == workload_id)


def test_chooses_earliest_start_and_site_order_tie_break() -> None:
    result = schedule(
        [site("site-b"), site("site-a")],
        [workload("w")],
        grid_for({"site-a": [0.1, 0.1], "site-b": [0.9, 0.9]}),
    )

    decision = result.decisions[0]
    assert decision.start_time == START
    assert decision.site_id == "site-b"


def test_respects_eligibility() -> None:
    result = schedule(
        [site("site-a"), site("site-b")],
        [workload("w", eligible=("site-b",))],
        grid_for({"site-a": [0.1], "site-b": [0.9]}),
    )

    assert result.decisions[0].site_id == "site-b"


def test_respects_overlapping_capacity() -> None:
    workloads = [
        workload("a", demand=8, duration=2),
        workload("b", demand=8, deadline_hour=3, eligible=("site-a",)),
    ]
    result = schedule(
        [site("site-a")], workloads, grid_for({"site-a": [0.2, 0.2, 0.2]})
    )

    assert placement(result, "a").start_time == START
    assert placement(result, "b").start_time == START + timedelta(hours=2)


def test_output_does_not_depend_on_workload_input_order() -> None:
    workloads = [workload("b"), workload("a")]
    sites = [site("site-a")]
    grid = grid_for({"site-a": [0.2, 0.2, 0.2]})

    assert schedule(sites, workloads, grid) == schedule(sites, reversed(workloads), grid)


def test_thermal_scores_do_not_change_placement_but_annotate_exposure() -> None:
    sites = [site("site-a"), site("site-b")]
    job = workload("w")
    cool_first = schedule(sites, [job], grid_for({"site-a": [0.1], "site-b": [0.9]}))
    hot_first = schedule(sites, [job], grid_for({"site-a": [0.8], "site-b": [0.1]}))

    assert cool_first.decisions[0].site_id == hot_first.decisions[0].site_id == "site-a"
    assert cool_first.decisions[0].thermal_exposure == pytest.approx(0.1)
    assert hot_first.decisions[0].thermal_exposure == pytest.approx(0.8)


@pytest.mark.parametrize(
    "job",
    [
        workload("unknown", eligible=("missing-site",)),
        workload("too-large", demand=9, eligible=("site-a",)),
        workload("deadline", duration=2, deadline_hour=1, eligible=("site-a",)),
    ],
)
def test_invalid_placement_conditions_become_unscheduled(job: Workload) -> None:
    result = schedule([site("site-a")], [job], grid_for({"site-a": [0.2, 0.2]}))

    assert result.unscheduled_workload_ids == (job.workload_id,)


def test_duplicate_site_and_workload_ids_are_rejected() -> None:
    grid = grid_for({"site-a": [0.2]})
    with pytest.raises(SchedulingInputError, match="duplicate site"):
        schedule([site("site-a"), site("site-a")], [], grid)
    with pytest.raises(SchedulingInputError, match="duplicate workload"):
        schedule([site("site-a")], [workload("w"), workload("w")], grid)
