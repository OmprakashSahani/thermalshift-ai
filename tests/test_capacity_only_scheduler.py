"""Tests for the Capacity Only baseline."""

import pytest

from tests.test_first_available_scheduler import START, grid_for, placement, site, workload
from thermalshift.scheduler.capacity_only import schedule


def test_selects_largest_minimum_residual_capacity() -> None:
    result = schedule(
        [site("site-a", 8), site("site-b", 16)],
        [workload("w", demand=4)],
        grid_for({"site-a": [0.1], "site-b": [0.9]}),
    )

    assert result.decisions[0].site_id == "site-b"


def test_residual_capacity_considers_entire_duration() -> None:
    jobs = [
        workload("a", demand=8, duration=1, eligible=("site-b",)),
        workload("b", demand=4, duration=2),
    ]
    result = schedule(
        [site("site-a", 8), site("site-b", 12)],
        jobs,
        grid_for({"site-a": [0.5, 0.5], "site-b": [0.5, 0.5]}),
    )

    assert placement(result, "a").site_id == "site-b"
    assert placement(result, "b").site_id == "site-a"


def test_ties_prefer_earlier_start_then_site_order() -> None:
    result = schedule(
        [site("site-b"), site("site-a")],
        [workload("w", release_hour=0, deadline_hour=2)],
        grid_for({"site-a": [0.2, 0.2], "site-b": [0.2, 0.2]}),
    )

    assert result.decisions[0].start_time == START
    assert result.decisions[0].site_id == "site-b"


def test_thermal_scores_do_not_change_placement_but_annotate_exposure() -> None:
    sites = [site("site-a", 8), site("site-b", 16)]
    job = workload("w", demand=4)
    first = schedule(sites, [job], grid_for({"site-a": [0.1], "site-b": [0.9]}))
    second = schedule(sites, [job], grid_for({"site-a": [0.9], "site-b": [0.2]}))

    assert first.decisions[0].site_id == second.decisions[0].site_id == "site-b"
    assert first.decisions[0].thermal_exposure == pytest.approx(0.9)
    assert second.decisions[0].thermal_exposure == pytest.approx(0.2)


def test_capacity_is_respected_across_overlapping_interval() -> None:
    jobs = [
        workload("a", demand=8, duration=2, deadline_hour=4),
        workload("b", demand=8, duration=2, deadline_hour=4),
    ]
    result = schedule(
        [site("site-a", 8)],
        jobs,
        grid_for({"site-a": [0.2, 0.2, 0.2, 0.2]}),
    )

    assert placement(result, "a").end_time <= placement(result, "b").start_time
