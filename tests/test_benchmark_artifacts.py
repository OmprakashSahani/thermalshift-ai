"""Offline tests for deterministic benchmark evidence artifacts."""

import json
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

import examples.run_historical_replay as historical_cli
import examples.run_synthetic_benchmark as synthetic_cli
from examples.run_historical_replay import main as historical_main
from examples.run_synthetic_benchmark import main as synthetic_main
from tests.test_replay_adapter import complete_cache
from thermalshift.benchmark.artifacts import (
    ARTIFACT_SCHEMA_VERSION,
    REQUEST_TIME_INTERPRETATION,
    HistoricalProvenance,
    benchmark_artifact_dict,
    build_benchmark_artifact,
    render_benchmark_markdown,
    write_benchmark_artifacts,
    write_benchmark_json,
)
from thermalshift.benchmark.models import BenchmarkReport, BenchmarkRun
from thermalshift.benchmark.runner import run_benchmark
from thermalshift.benchmark.synthetic import create_synthetic_scenario
from thermalshift.fortyguard.cache import HeatmapResultCache
from thermalshift.replay.adapter import (
    build_historical_replay_scenario,
    load_calibration_status,
)
from thermalshift.replay.plan import SUMMER_WINDOW

FIXED_TIME = datetime(2026, 8, 25, 12, 30, tzinfo=UTC)


def controlled_timer():
    """Return a timer producing 2.5 ms for every scheduler run."""
    current = 0

    def timer() -> int:
        nonlocal current
        value = current
        current += 2_500_000
        return value

    return timer


def synthetic_artifact():
    scenario = create_synthetic_scenario()
    report = run_benchmark(scenario, timer=controlled_timer())
    return build_benchmark_artifact(
        scenario,
        report,
        evidence_type="synthetic_demonstration",
        generated_at_utc=FIXED_TIME,
    )


def historical_artifact(tmp_path: Path):
    cache = complete_cache(tmp_path)
    scenario = build_historical_replay_scenario(SUMMER_WINDOW, cache)
    report = run_benchmark(scenario, timer=controlled_timer())
    calibration = load_calibration_status(cache)
    return build_benchmark_artifact(
        scenario,
        report,
        evidence_type="fortyguard_historical_replay",
        generated_at_utc=FIXED_TIME,
        provenance=HistoricalProvenance(
            replay_window_id=SUMMER_WINDOW.window_id,
            replay_start_utc=SUMMER_WINDOW.start_utc,
            replay_slot_count=SUMMER_WINDOW.slot_count,
            calibration_observation_count=calibration.available_count,
            calibration_lower_reference_c=calibration.lower_reference_c,
            calibration_upper_reference_c=calibration.upper_reference_c,
        ),
    )


def test_synthetic_artifact_has_complete_safe_inputs_metrics_and_decisions() -> None:
    artifact = synthetic_artifact()
    value = benchmark_artifact_dict(artifact)

    assert value["artifact_schema_version"] == ARTIFACT_SCHEMA_VERSION
    assert value["evidence_type"] == "synthetic_demonstration"
    assert "not FortyGuard evidence" in value["evidence_boundaries"]["evidence_classification"]
    assert all("modeled_gpu_capacity" in site for site in value["sites"])
    assert all("total_gpu_capacity" not in site for site in value["sites"])
    assert value["workloads"][0].keys() == {
        "workload_id",
        "name",
        "gpu_demand",
        "duration_hours",
        "release_time",
        "deadline",
        "priority",
        "eligible_site_ids",
    }
    run = value["scheduler_runs"][0]
    expected_metrics = {
        "scheduler_name",
        "total_workloads",
        "scheduled_count",
        "unscheduled_count",
        "completion_rate",
        "deadline_satisfaction_count",
        "deadline_satisfaction_rate",
        "scheduled_workload_ids",
        "unscheduled_workload_ids",
        "total_scheduled_workload_hours",
        "total_thermal_exposure_stress_hours",
        "mean_thermal_exposure_per_scheduled_workload",
        "mean_occupied_thermal_stress",
        "peak_occupied_thermal_stress",
        "runtime_ms",
        "decisions",
    }
    assert run.keys() == expected_metrics
    assert run["runtime_ms"] == 2.5
    assert run["decisions"]
    assert run["decisions"][0]["scheduler_name"] == run["scheduler_name"]


def test_historical_provenance_separates_real_temperature_and_modeled_inputs(
    tmp_path: Path,
) -> None:
    value = benchmark_artifact_dict(historical_artifact(tmp_path))
    provenance = value["provenance"]

    assert value["evidence_type"] == "fortyguard_historical_replay"
    assert provenance == {
        "replay_window_id": "summer-midday-v1",
        "replay_start_utc": "2024-07-15T18:00:00Z",
        "replay_slot_count": 6,
        "calibration_observation_count": 28,
        "calibration_lower_reference_c": 3.4000000000000004,
        "calibration_upper_reference_c": 23.6,
        "calibration_rule": "pooled_p10_p90",
        "temperature_source": "fortyguard",
        "workload_source": "modeled",
        "site_capacity_source": "modeled",
        "request_time_interpretation": REQUEST_TIME_INTERPRETATION,
    }
    boundary = value["evidence_boundaries"]["evidence_classification"]
    assert "Ambient temperatures come from FortyGuard" in boundary
    assert "not real customer workloads" in boundary


def test_comparisons_preserve_existing_fairness_and_negative_percentages() -> None:
    scenario = create_synthetic_scenario()
    report = run_benchmark(scenario, timer=controlled_timer())
    baseline, capacity, candidate = report.runs
    unequal_metrics = replace(
        candidate.metrics,
        scheduled_count=candidate.metrics.scheduled_count - 1,
        unscheduled_count=1,
        completion_rate=(candidate.metrics.scheduled_count - 1) / candidate.metrics.total_workloads,
        deadline_satisfied_count=candidate.metrics.deadline_satisfied_count - 1,
        deadline_satisfaction_rate=(candidate.metrics.deadline_satisfied_count - 1)
        / candidate.metrics.total_workloads,
        scheduled_workload_ids=candidate.metrics.scheduled_workload_ids[:-1],
        unscheduled_workload_ids=(candidate.metrics.scheduled_workload_ids[-1],),
    )
    unequal_report = replace(
        report,
        runs=(baseline, capacity, BenchmarkRun(candidate.result, unequal_metrics)),
    )
    unequal = build_benchmark_artifact(
        scenario, unequal_report, evidence_type="synthetic_demonstration"
    )
    assert all(item["thermal_exposure_reduction_pct"] is None for item in unequal.comparisons)

    worse_metrics = replace(
        candidate.metrics,
        total_thermal_exposure_stress_hours=(
            baseline.metrics.total_thermal_exposure_stress_hours * 1.2
        ),
    )
    worse_report = BenchmarkReport(
        report.scenario_id,
        report.description,
        report.data_source_label,
        (baseline, capacity, BenchmarkRun(candidate.result, worse_metrics)),
    )
    worse = build_benchmark_artifact(
        scenario, worse_report, evidence_type="synthetic_demonstration"
    )
    assert worse.comparisons[0]["thermal_exposure_reduction_pct"] == pytest.approx(-20.0)


def test_json_and_markdown_are_deterministic_safe_and_round_trip(tmp_path: Path) -> None:
    artifact = synthetic_artifact()
    first = tmp_path / "one" / "benchmark.json"
    second = tmp_path / "two" / "benchmark.json"
    write_benchmark_json(artifact, first)
    write_benchmark_json(artifact, second)

    assert first.read_bytes() == second.read_bytes()
    parsed = json.loads(first.read_text(encoding="utf-8"))
    assert parsed == benchmark_artifact_dict(artifact)
    assert first.read_bytes().endswith(b"\n")
    rendered = render_benchmark_markdown(artifact)
    assert rendered == render_benchmark_markdown(artifact)
    assert "| Scheduler | Scheduled |" in rendered
    assert "SYNTHETIC DEMONSTRATION — NOT FORTYGUARD BENCHMARK EVIDENCE" in rendered
    assert "GPU temperature" in rendered
    assert "| 2.500 |" in rendered
    serialized = first.read_text(encoding="utf-8")
    for forbidden in ("api_key", "map_data", "activity_id", "cache_key", "payload"):
        assert forbidden not in serialized


def test_historical_markdown_classification(tmp_path: Path) -> None:
    rendered = render_benchmark_markdown(historical_artifact(tmp_path))
    assert "FORTYGUARD-BACKED HISTORICAL REPLAY" in rendered
    assert "REAL HISTORICAL AMBIENT TEMPERATURES + MODELED WORKLOADS" in rendered
    assert REQUEST_TIME_INTERPRETATION in rendered


def test_writers_create_output_directory(tmp_path: Path) -> None:
    output_dir = tmp_path / "nested" / "artifact"
    paths = write_benchmark_artifacts(synthetic_artifact(), output_dir)
    assert paths == (output_dir / "benchmark.json", output_dir / "report.md")
    assert all(path.is_file() for path in paths)


def test_synthetic_cli_artifacts_use_report_runtime_without_timer_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenario = create_synthetic_scenario()
    supplied_report = run_benchmark(scenario, timer=controlled_timer())
    calls = []

    def run_with_default_timing(received_scenario):
        calls.append(received_scenario)
        return supplied_report

    monkeypatch.setattr(synthetic_cli, "run_benchmark", run_with_default_timing)
    output_dir = tmp_path / "synthetic-runtime"
    synthetic_cli.main(["--output-dir", str(output_dir)])

    artifact = json.loads((output_dir / "benchmark.json").read_text(encoding="utf-8"))
    assert len(calls) == 1
    assert calls[0].scenario_id == scenario.scenario_id
    assert [run["runtime_ms"] for run in artifact["scheduler_runs"]] == [2.5] * 3


def test_historical_cli_artifacts_use_report_runtime_without_timer_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = complete_cache(tmp_path / "cache")
    scenario = build_historical_replay_scenario(SUMMER_WINDOW, cache)
    supplied_report = run_benchmark(scenario, timer=controlled_timer())
    calls = []

    def run_with_default_timing(received_scenario):
        calls.append(received_scenario)
        return supplied_report

    monkeypatch.setattr(historical_cli, "run_benchmark", run_with_default_timing)
    output_dir = tmp_path / "historical-runtime"
    result = historical_cli.main(["--output-dir", str(output_dir)], cache)

    artifact = json.loads((output_dir / "benchmark.json").read_text(encoding="utf-8"))
    assert result == 0
    assert len(calls) == 1
    assert calls[0].scenario_id == scenario.scenario_id
    assert [run["runtime_ms"] for run in artifact["scheduler_runs"]] == [2.5] * 3


def test_synthetic_script_writes_artifacts_and_runs_from_repository_root(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "synthetic"
    repository_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [
            sys.executable,
            "examples/run_synthetic_benchmark.py",
            "--output-dir",
            str(output_dir),
        ],
        cwd=repository_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    assert (output_dir / "benchmark.json").is_file()
    assert (output_dir / "report.md").is_file()


def test_incomplete_historical_replay_writes_no_artifacts(tmp_path: Path) -> None:
    output_dir = tmp_path / "must-not-exist"
    result = historical_main(
        ["--output-dir", str(output_dir)], HeatmapResultCache(tmp_path / "cache")
    )
    assert result == 1
    assert not output_dir.exists()


def test_synthetic_main_without_output_directory_remains_supported(capsys) -> None:
    synthetic_main([])
    assert "SYNTHETIC DEMONSTRATION" in capsys.readouterr().out
