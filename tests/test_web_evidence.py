"""Offline tests for the committed-evidence web adapter."""

import json
from pathlib import Path

import pytest

from thermalshift.web.evidence import EvidenceLoadError, load_all_evidence, load_window_evidence

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = REPOSITORY_ROOT / "evidence"


def test_all_evidence_contains_both_historical_windows_with_summer_primary() -> None:
    result = load_all_evidence(EVIDENCE_ROOT)

    assert result["evidence_type"] == "fortyguard_historical_replay"
    assert result["default_window_id"] == "summer-midday-v1"
    assert [window["window_id"] for window in result["windows"]] == [
        "summer-midday-v1",
        "winter-overnight-v1",
    ]
    assert result["windows"][0]["is_primary"] is True
    assert result["windows"][1]["role"] == "robustness"


def test_summer_values_are_read_exactly_from_committed_artifact() -> None:
    result = load_window_evidence(EVIDENCE_ROOT, "summer-midday-v1")
    runs = {run["scheduler_name"]: run for run in result["schedulers"]}
    comparisons = {
        comparison["baseline_scheduler"]: comparison
        for comparison in result["comparisons"]
    }

    assert tuple(runs) == ("first_available", "capacity_only", "thermalshift")
    assert runs["first_available"]["total_thermal_exposure_stress_hours"] == (
        16.59187515444705
    )
    assert runs["capacity_only"]["total_thermal_exposure_stress_hours"] == (
        16.252813396684626
    )
    assert runs["thermalshift"]["total_thermal_exposure_stress_hours"] == (
        13.261829063112446
    )
    assert comparisons["first_available"]["thermal_exposure_reduction_pct"] == (
        20.070342021842333
    )
    assert comparisons["capacity_only"]["thermal_exposure_reduction_pct"] == (
        18.40287130954389
    )
    assert all(run["scheduled_count"] == 10 for run in runs.values())
    assert all(run["deadline_satisfaction_rate"] == 1.0 for run in runs.values())


def test_normalized_evidence_has_sites_decisions_and_safe_provenance() -> None:
    result = load_window_evidence(EVIDENCE_ROOT, "summer-midday-v1")

    assert result["workload_count"] == 10
    assert len(result["sites"]) == 4
    assert all(site["classification"] == "Modeled benchmark site" for site in result["sites"])
    assert all(site["modeled_gpu_capacity"] == 64 for site in result["sites"])
    assert all(len(run["decisions"]) == 10 for run in result["schedulers"])
    assert result["provenance"]["calibration_observation_count"] == 28
    assert result["provenance"]["calibration_lower_reference_c"] == 4.567570294117648
    assert result["provenance"]["calibration_upper_reference_c"] == 37.01878625
    assert result["provenance"]["temperature_source"] == "fortyguard"
    assert result["provenance"]["workload_source"] == "modeled"
    assert result["provenance"]["site_capacity_source"] == "modeled"
    assert "modeled scheduling metric" in result["scientific_boundaries"]["modeled_metric"]


def test_winter_exposes_value_derived_zero_floor_interpretation() -> None:
    result = load_window_evidence(EVIDENCE_ROOT, "winter-overnight-v1")
    runs = {run["scheduler_name"]: run for run in result["schedulers"]}

    assert runs["first_available"]["total_thermal_exposure_stress_hours"] == (
        0.1515727124128858
    )
    assert runs["capacity_only"]["total_thermal_exposure_stress_hours"] == (
        0.16763230958147451
    )
    assert runs["thermalshift"]["total_thermal_exposure_stress_hours"] == 0.0
    assert result["zero_floor"]["applies"] is True
    assert "Model-floor effect" in result["zero_floor"]["message"]
    assert "not 100% cooling, energy" in result["zero_floor"]["message"]


def test_normalized_output_excludes_sensitive_and_raw_fields() -> None:
    serialized = json.dumps(load_all_evidence(EVIDENCE_ROOT)).casefold()

    for forbidden in (
        "api_key",
        "activity_id",
        "cache_key",
        "map_data",
        "raw_payload",
        "authorization",
        "gmail",
        ".env",
    ):
        assert forbidden not in serialized


def test_missing_evidence_fails_without_fallback(tmp_path: Path) -> None:
    with pytest.raises(EvidenceLoadError, match="Committed evidence is missing"):
        load_window_evidence(tmp_path, "summer-midday-v1")


def test_malformed_evidence_fails_without_fallback(tmp_path: Path) -> None:
    path = tmp_path / "summer-midday-v1" / "benchmark.json"
    path.parent.mkdir(parents=True)
    path.write_text("{not-json}\n", encoding="utf-8")

    with pytest.raises(EvidenceLoadError, match="Committed evidence is unreadable"):
        load_window_evidence(tmp_path, "summer-midday-v1")


def test_wrong_evidence_classification_is_rejected(tmp_path: Path) -> None:
    source = json.loads(
        (EVIDENCE_ROOT / "summer-midday-v1" / "benchmark.json").read_text(encoding="utf-8")
    )
    source["evidence_type"] = "synthetic_demonstration"
    path = tmp_path / "summer-midday-v1" / "benchmark.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(source), encoding="utf-8")

    with pytest.raises(EvidenceLoadError, match="Unexpected evidence classification"):
        load_window_evidence(tmp_path, "summer-midday-v1")


def test_unexpected_comparison_identity_is_rejected_safely(tmp_path: Path) -> None:
    source = json.loads(
        (EVIDENCE_ROOT / "summer-midday-v1" / "benchmark.json").read_text(encoding="utf-8")
    )
    source["comparisons"][0]["baseline_scheduler"] = "unknown_baseline"
    path = tmp_path / "summer-midday-v1" / "benchmark.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(source), encoding="utf-8")

    with pytest.raises(EvidenceLoadError, match="Unexpected comparison set or order"):
        load_window_evidence(tmp_path, "summer-midday-v1")
