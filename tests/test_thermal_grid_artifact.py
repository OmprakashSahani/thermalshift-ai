"""Offline export and strict-loader coverage for sanitized public grids."""

import json
from pathlib import Path

import pytest

from thermalshift.fortyguard.cache import HeatmapResultCache
from thermalshift.web.thermal_grid import (
    ThermalGridArtifactError,
    export_thermal_grid,
    load_thermal_grid_artifact,
)

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence"


@pytest.mark.parametrize("window_id", ["summer-midday-v1", "winter-overnight-v1"])
def test_cache_only_export_is_complete_deterministic_and_safe(window_id: str) -> None:
    artifact = export_thermal_grid(window_id, HeatmapResultCache(ROOT / "data/cache/fortyguard"))
    assert len(artifact["entries"]) == 24
    second = export_thermal_grid(
        window_id, HeatmapResultCache(ROOT / "data/cache/fortyguard")
    )
    assert artifact == second
    pairs = [(item["timestamp_utc"], item["site_id"]) for item in artifact["entries"]]
    assert pairs == sorted(pairs)
    serialized = json.dumps(artifact).casefold()
    for forbidden in ("api_key", "activity_id", "cache_key", "map_data", "polygon", "email"):
        assert forbidden not in serialized


def _copy_artifacts(tmp_path: Path) -> dict[str, object]:
    target = tmp_path / "summer-midday-v1"
    target.mkdir()
    benchmark = EVIDENCE / "summer-midday-v1" / "benchmark.json"
    (target / "benchmark.json").write_bytes(benchmark.read_bytes())
    raw = json.loads((EVIDENCE / "summer-midday-v1" / "thermal_grid.json").read_text())
    return raw


def _write(tmp_path: Path, raw: dict[str, object]) -> None:
    (tmp_path / "summer-midday-v1" / "thermal_grid.json").write_text(json.dumps(raw))


@pytest.mark.parametrize(
    "mutation", ["wrong_window", "duplicate", "bad_score", "bad_source", "unordered"]
)
def test_malformed_artifact_is_rejected(tmp_path: Path, mutation: str) -> None:
    raw = _copy_artifacts(tmp_path)
    if mutation == "wrong_window":
        raw["window_id"] = "winter-overnight-v1"
    elif mutation == "duplicate":
        raw["entries"][1] = raw["entries"][0]
    elif mutation == "bad_score":
        raw["entries"][0]["thermal_stress_score"] = 1.1
    elif mutation == "unordered":
        raw["entries"][0], raw["entries"][1] = raw["entries"][1], raw["entries"][0]
    else:
        raw["temperature_source"] = "unknown"
    _write(tmp_path, raw)
    with pytest.raises(ThermalGridArtifactError):
        load_thermal_grid_artifact(tmp_path, "summer-midday-v1")


def test_committed_grids_load_with_exact_coverage() -> None:
    for window_id in ("summer-midday-v1", "winter-overnight-v1"):
        artifact, grid = load_thermal_grid_artifact(EVIDENCE, window_id)
        assert len(artifact["entries"]) == 24
        assert len(grid.available_timestamps()) == 6
