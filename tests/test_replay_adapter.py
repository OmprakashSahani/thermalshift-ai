from pathlib import Path

import pytest

from examples.run_historical_replay import main as run_replay_main
from thermalshift.benchmark.runner import run_benchmark
from thermalshift.domain.sites import get_default_sites
from thermalshift.fortyguard.cache import HeatmapResultCache
from thermalshift.fortyguard.models import (
    DistributionSeries,
    HeatmapResult,
    HeatmapStats,
    TemperatureStats,
)
from thermalshift.fortyguard.payloads import build_historical_heatmap_payload
from thermalshift.replay.adapter import (
    HISTORICAL_DATA_SOURCE_LABEL,
    build_historical_replay_scenario,
    build_historical_thermal_grid,
    load_calibration_status,
    load_replay_observations,
)
from thermalshift.replay.models import ReplayDataIncompleteError
from thermalshift.replay.plan import (
    SUMMER_WINDOW,
    build_calibration_plan,
    build_replay_plan,
)
from thermalshift.thermal.model import ThermalStressModel


def result(mean: float) -> HeatmapResult:
    series = DistributionSeries(x_axis=[], y_axis=[])
    return HeatmapResult(
        map_data={},
        stats_data=HeatmapStats(
            temperature_stats=TemperatureStats(
                minimum=mean - 1,
                maximum=mean + 1,
                mean=mean,
                standard_deviation=0.5,
            ),
            overall_temperature_distribution=[],
            normal_temperature_distribution=series,
            temperature_frequency=series,
        ),
    )


def put_entries(cache: HeatmapResultCache, entries, values) -> None:
    sites = {site.site_id: site for site in get_default_sites()}
    for entry, value in zip(entries, values, strict=True):
        payload = build_historical_heatmap_payload(
            sites[entry.site_id], entry.requested_utc
        )
        cache.put(payload, result(value))


def complete_cache(path: Path) -> HeatmapResultCache:
    cache = HeatmapResultCache(path)
    calibration = build_calibration_plan(cache)
    put_entries(cache, calibration, range(28))
    replay = build_replay_plan(SUMMER_WINDOW, cache).entries
    put_entries(cache, replay, (10 + index / 2 for index in range(24)))
    return cache


def test_complete_replay_uses_mean_and_preserves_requested_instants(tmp_path: Path) -> None:
    cache = HeatmapResultCache(tmp_path)
    entries = build_replay_plan(SUMMER_WINDOW, cache).entries
    put_entries(cache, entries, (20 + index for index in range(24)))
    observations = load_replay_observations(SUMMER_WINDOW, cache)
    assert len(observations) == 24
    assert observations[0].temperature_c == 20
    assert observations[0].timestamp == SUMMER_WINDOW.start_utc
    assert observations[-1].temperature_c == 43
    assert {item.source for item in observations} == {"fortyguard"}


def test_missing_replay_is_explicit_with_no_fallback(tmp_path: Path) -> None:
    cache = HeatmapResultCache(tmp_path)
    entries = build_replay_plan(SUMMER_WINDOW, cache).entries
    put_entries(cache, entries[:-1], range(23))
    with pytest.raises(ReplayDataIncompleteError) as caught:
        load_replay_observations(SUMMER_WINDOW, cache)
    assert caught.value.available_count == 23
    assert caught.value.missing_entries == (entries[-1],)


def test_calibration_complete_and_partial_status(tmp_path: Path) -> None:
    cache = HeatmapResultCache(tmp_path)
    entries = build_calibration_plan(cache)
    put_entries(cache, entries[:27], range(27))
    partial = load_calibration_status(cache)
    assert partial.available_count == 27
    assert not partial.complete
    assert partial.diagnostics is not None
    assert partial.lower_reference_c == pytest.approx(partial.diagnostics.p10_c)
    assert partial.upper_reference_c == pytest.approx(partial.diagnostics.p90_c)

    put_entries(cache, entries[27:], (27,))
    complete = load_calibration_status(cache)
    assert complete.official_ready
    assert complete.available_count == 28
    assert complete.lower_reference_c == pytest.approx(2.7)
    assert complete.upper_reference_c == pytest.approx(24.3)


def test_equal_calibration_references_are_rejected_clearly(tmp_path: Path) -> None:
    cache = HeatmapResultCache(tmp_path)
    entries = build_calibration_plan(cache)
    put_entries(cache, entries, (20 for _ in entries))
    status = load_calibration_status(cache)
    assert status.complete
    assert not status.official_ready
    assert "distinct and ordered" in (status.reference_error or "")
    with pytest.raises(ReplayDataIncompleteError, match="distinct and ordered"):
        build_historical_thermal_grid(SUMMER_WINDOW, cache)


def test_complete_grid_uses_common_thermal_model_scores(tmp_path: Path) -> None:
    cache = complete_cache(tmp_path)
    status = load_calibration_status(cache)
    grid = build_historical_thermal_grid(SUMMER_WINDOW, cache)
    observations = load_replay_observations(SUMMER_WINDOW, cache)
    model = ThermalStressModel(status.lower_reference_c, status.upper_reference_c)
    assert sum(len(grid.available_timestamps(site.site_id)) for site in get_default_sites()) == 24
    for observation in observations:
        score = grid.get_score(observation.site_id, observation.timestamp)
        assert 0 <= score <= 1
        assert score == model.assess(observation).thermal_stress_score
        assert score != observation.temperature_c


def test_complete_scenario_runs_all_existing_schedulers(tmp_path: Path) -> None:
    scenario = build_historical_replay_scenario(
        SUMMER_WINDOW, complete_cache(tmp_path)
    )
    assert scenario.data_source_label == HISTORICAL_DATA_SOURCE_LABEL
    assert "modeled benchmark parameters" in scenario.description
    report = run_benchmark(scenario)
    assert tuple(run.metrics.scheduler_name for run in report.runs) == (
        "first_available",
        "capacity_only",
        "thermalshift",
    )
    assert {run.metrics.scheduled_count for run in report.runs} == {10}


def test_incomplete_calibration_blocks_official_scenario(tmp_path: Path) -> None:
    with pytest.raises(ReplayDataIncompleteError) as caught:
        build_historical_replay_scenario(SUMMER_WINDOW, HeatmapResultCache(tmp_path))
    assert caught.value.data_kind == "calibration"


def test_incomplete_replay_blocks_official_scenario(tmp_path: Path) -> None:
    cache = HeatmapResultCache(tmp_path)
    calibration = build_calibration_plan(cache)
    put_entries(cache, calibration, range(28))
    with pytest.raises(ReplayDataIncompleteError) as caught:
        build_historical_replay_scenario(SUMMER_WINDOW, cache)
    assert caught.value.data_kind == "replay"
    assert caught.value.available_count == 4


def test_offline_runner_incomplete_and_complete_paths(tmp_path: Path, capsys) -> None:
    assert run_replay_main([], HeatmapResultCache(tmp_path / "empty")) == 1
    incomplete_output = capsys.readouterr().out
    assert "INCOMPLETE — NO BENCHMARK WAS RUN" in incomplete_output
    assert "Synthetic replacement and interpolation are disabled" in incomplete_output

    assert run_replay_main([], complete_cache(tmp_path / "complete")) == 0
    complete_output = capsys.readouterr().out
    assert "FORTYGUARD-BACKED HISTORICAL REPLAY" in complete_output
    assert "REAL HISTORICAL AMBIENT TEMPERATURES + MODELED WORKLOADS" in complete_output
