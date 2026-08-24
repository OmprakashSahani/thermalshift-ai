from datetime import timedelta

from thermalshift.domain.sites import get_default_sites
from thermalshift.replay.plan import SUMMER_WINDOW, WINTER_WINDOW
from thermalshift.replay.workloads import build_replay_workloads
from thermalshift.scheduler import (
    ThermalGrid,
    ThermalGridEntry,
    schedule_capacity_only,
    schedule_first_available,
    schedule_thermalshift,
)


def test_fixed_modeled_workload_shape_and_relative_timing() -> None:
    summer = build_replay_workloads(SUMMER_WINDOW)
    winter = build_replay_workloads(WINTER_WINDOW)
    assert len(summer) == 10
    assert len({item.workload_id for item in summer}) == 10
    assert summer == build_replay_workloads(SUMMER_WINDOW)
    assert {item.duration_hours for item in summer} == {1, 2, 3}
    assert len({item.gpu_demand for item in summer}) > 1
    assert any(len(item.eligible_site_ids) == 4 for item in summer)
    assert any(len(item.eligible_site_ids) == 2 for item in summer)
    shift = WINTER_WINDOW.start_utc - SUMMER_WINDOW.start_utc
    for summer_item, winter_item in zip(summer, winter, strict=True):
        assert summer_item.release_time.tzinfo is not None
        assert summer_item.deadline <= SUMMER_WINDOW.start_utc + timedelta(hours=6)
        assert winter_item.release_time == summer_item.release_time + shift
        assert winter_item.deadline == summer_item.deadline + shift
        assert winter_item.model_dump(exclude={"release_time", "deadline"}) == (
            summer_item.model_dump(exclude={"release_time", "deadline"})
        )


def test_all_schedulers_place_all_workloads_on_constant_complete_grid() -> None:
    sites = get_default_sites()
    workloads = build_replay_workloads(SUMMER_WINDOW)
    grid = ThermalGrid(
        ThermalGridEntry(site.site_id, instant, 0.5)
        for site in sites
        for instant in SUMMER_WINDOW.instants
    )
    results = (
        schedule_first_available(sites, workloads, grid),
        schedule_capacity_only(sites, workloads, grid),
        schedule_thermalshift(sites, workloads, grid),
    )
    assert {result.scheduled_count for result in results} == {10}
    assert all(not result.unscheduled_workload_ids for result in results)
