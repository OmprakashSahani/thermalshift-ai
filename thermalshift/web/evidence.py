"""Load and normalize committed historical benchmark evidence for the web demo."""

import json
from math import isclose
from pathlib import Path
from typing import Any

WINDOW_IDS = ("summer-midday-v1", "winter-overnight-v1")
PRIMARY_WINDOW_ID = "summer-midday-v1"
WINDOW_PRESENTATION = {
    "summer-midday-v1": {"label": "Summer midday", "role": "primary"},
    "winter-overnight-v1": {"label": "Winter overnight", "role": "robustness"},
}
SITE_LOCATIONS = {
    "ashburn-va": "Ashburn, Virginia",
    "phoenix-az": "Phoenix, Arizona",
    "san-antonio-tx": "San Antonio, Texas",
    "atlanta-ga": "Atlanta, Georgia",
}
EXPECTED_SCHEDULERS = ("first_available", "capacity_only", "thermalshift")


class EvidenceLoadError(RuntimeError):
    """Raised when committed evidence is absent or does not match the expected schema."""


def load_all_evidence(evidence_root: Path) -> dict[str, object]:
    """Load both predeclared windows into a compact, display-safe representation."""
    windows = [load_window_evidence(evidence_root, window_id) for window_id in WINDOW_IDS]
    return {
        "evidence_type": "fortyguard_historical_replay",
        "evidence_label": "FORTYGUARD-BACKED HISTORICAL EVIDENCE",
        "default_window_id": PRIMARY_WINDOW_ID,
        "windows": windows,
    }


def load_window_evidence(evidence_root: Path, window_id: str) -> dict[str, object]:
    """Load one known committed replay window, rejecting missing or malformed evidence."""
    if window_id not in WINDOW_IDS:
        raise KeyError(window_id)

    path = evidence_root / window_id / "benchmark.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise EvidenceLoadError(f"Committed evidence is missing for {window_id}") from error
    except (OSError, json.JSONDecodeError) as error:
        raise EvidenceLoadError(f"Committed evidence is unreadable for {window_id}") from error

    artifact = _mapping(raw, "artifact")
    evidence_type = _text(artifact, "evidence_type")
    if evidence_type != "fortyguard_historical_replay":
        raise EvidenceLoadError(f"Unexpected evidence classification for {window_id}")

    provenance = _mapping(artifact.get("provenance"), "provenance")
    if _text(provenance, "replay_window_id") != window_id:
        raise EvidenceLoadError(f"Replay provenance does not match {window_id}")

    sites = [_normalize_site(item) for item in _sequence(artifact, "sites")]
    workloads = _sequence(artifact, "workloads")
    workload_ids = [_text(_mapping(item, "workload"), "workload_id") for item in workloads]
    schedulers = [
        _normalize_scheduler(item, sites) for item in _sequence(artifact, "scheduler_runs")
    ]
    scheduler_names = tuple(item["scheduler_name"] for item in schedulers)
    if scheduler_names != EXPECTED_SCHEDULERS:
        raise EvidenceLoadError(f"Unexpected scheduler set or order for {window_id}")

    comparisons = [_normalize_comparison(item) for item in _sequence(artifact, "comparisons")]
    comparison_pairs = tuple(
        (item["baseline_scheduler"], item["candidate_scheduler"]) for item in comparisons
    )
    if comparison_pairs != (
        ("first_available", "thermalshift"),
        ("capacity_only", "thermalshift"),
    ):
        raise EvidenceLoadError(f"Unexpected comparison set or order for {window_id}")
    boundaries = _mapping(artifact.get("evidence_boundaries"), "evidence_boundaries")
    not_measured = [
        _plain_text(item, "scientific boundary")
        for item in _sequence(boundaries, "not_measured_or_proven")
    ]
    zero_floor = _zero_floor_interpretation(schedulers, comparisons)
    presentation = WINDOW_PRESENTATION[window_id]

    return {
        "window_id": window_id,
        "label": presentation["label"],
        "role": presentation["role"],
        "is_primary": window_id == PRIMARY_WINDOW_ID,
        "evidence_type": evidence_type,
        "scenario_id": _text(artifact, "scenario_id"),
        "scenario_description": _text(artifact, "scenario_description"),
        "provenance": {
            "replay_start_utc": _text(provenance, "replay_start_utc"),
            "replay_slot_count": _number(provenance, "replay_slot_count"),
            "calibration_observation_count": _number(
                provenance, "calibration_observation_count"
            ),
            "calibration_rule": _text(provenance, "calibration_rule"),
            "calibration_lower_reference_c": _number(
                provenance, "calibration_lower_reference_c"
            ),
            "calibration_upper_reference_c": _number(
                provenance, "calibration_upper_reference_c"
            ),
            "request_time_interpretation": _text(
                provenance, "request_time_interpretation"
            ),
            "temperature_source": _text(provenance, "temperature_source"),
            "workload_source": _text(provenance, "workload_source"),
            "site_capacity_source": _text(provenance, "site_capacity_source"),
        },
        "sites": sites,
        "workload_count": len(workloads),
        "workload_ids": workload_ids,
        "schedulers": schedulers,
        "comparisons": comparisons,
        "zero_floor": zero_floor,
        "scientific_boundaries": {
            "modeled_metric": _text(boundaries, "thermal_stress_hours"),
            "not_measured_or_proven": not_measured,
            "evidence_classification": _text(boundaries, "evidence_classification"),
        },
    }


def _normalize_site(value: object) -> dict[str, object]:
    site = _mapping(value, "site")
    site_id = _text(site, "site_id")
    if site_id not in SITE_LOCATIONS:
        raise EvidenceLoadError(f"Unexpected modeled site {site_id}")
    return {
        "site_id": site_id,
        "name": _text(site, "name"),
        "location": SITE_LOCATIONS[site_id],
        "latitude": _number(site, "latitude"),
        "longitude": _number(site, "longitude"),
        "timezone": _text(site, "timezone"),
        "modeled_gpu_capacity": _number(site, "modeled_gpu_capacity"),
        "classification": "Modeled benchmark site",
    }


def _normalize_scheduler(value: object, sites: list[dict[str, object]]) -> dict[str, object]:
    run = _mapping(value, "scheduler run")
    site_names = {str(site["site_id"]): str(site["location"]) for site in sites}
    decisions = []
    for value_decision in _sequence(run, "decisions"):
        decision = _mapping(value_decision, "schedule decision")
        site_id = _text(decision, "site_id")
        if site_id not in site_names:
            raise EvidenceLoadError(f"Decision references unknown modeled site {site_id}")
        decisions.append(
            {
                "workload_id": _text(decision, "workload_id"),
                "site_id": site_id,
                "site_location": site_names[site_id],
                "start_time": _text(decision, "start_time"),
                "end_time": _text(decision, "end_time"),
                "thermal_exposure": _number(decision, "thermal_exposure"),
                "thermal_stress_avg": _number(decision, "thermal_stress_avg"),
                "deadline_satisfied": _boolean(decision, "deadline_satisfied"),
                "capacity_satisfied": _boolean(decision, "capacity_satisfied"),
            }
        )
    return {
        "scheduler_name": _text(run, "scheduler_name"),
        "scheduled_count": _number(run, "scheduled_count"),
        "total_workloads": _number(run, "total_workloads"),
        "completion_rate": _number(run, "completion_rate"),
        "deadline_satisfaction_rate": _number(run, "deadline_satisfaction_rate"),
        "total_thermal_exposure_stress_hours": _number(
            run, "total_thermal_exposure_stress_hours"
        ),
        "mean_occupied_thermal_stress": _number(run, "mean_occupied_thermal_stress"),
        "peak_occupied_thermal_stress": _number(run, "peak_occupied_thermal_stress"),
        "scheduled_workload_ids": [
            _plain_text(item, "scheduled workload ID")
            for item in _sequence(run, "scheduled_workload_ids")
        ],
        "decisions": decisions,
    }


def _normalize_comparison(value: object) -> dict[str, object]:
    comparison = _mapping(value, "comparison")
    reduction = comparison.get("thermal_exposure_reduction_pct")
    return {
        "baseline_scheduler": _text(comparison, "baseline_scheduler"),
        "candidate_scheduler": _text(comparison, "candidate_scheduler"),
        "same_scheduled_workload_set": _boolean(
            comparison, "same_scheduled_workload_set"
        ),
        "completion_preserved": _boolean(comparison, "completion_preserved"),
        "deadline_satisfaction_preserved": _boolean(
            comparison, "deadline_satisfaction_preserved"
        ),
        "direct_thermal_comparison_valid": _boolean(
            comparison, "direct_thermal_comparison_valid"
        ),
        "thermal_exposure_reduction_pct": (
            None if reduction is None else _finite_number(reduction, "comparison percentage")
        ),
        "headline": _text(comparison, "headline"),
    }


def _zero_floor_interpretation(
    schedulers: list[dict[str, object]], comparisons: list[dict[str, object]]
) -> dict[str, object]:
    runs = {str(item["scheduler_name"]): item for item in schedulers}
    candidate = runs["thermalshift"]
    candidate_exposure = float(candidate["total_thermal_exposure_stress_hours"])
    qualifying = []
    for comparison in comparisons:
        baseline_exposure = float(
            runs[str(comparison["baseline_scheduler"])][
                "total_thermal_exposure_stress_hours"
            ]
        )
        reduction = comparison["thermal_exposure_reduction_pct"]
        if baseline_exposure <= 0.0 or reduction is None:
            continue
        expected_reduction = 100 * (baseline_exposure - candidate_exposure) / baseline_exposure
        if comparison["direct_thermal_comparison_valid"] is True and isclose(
            float(reduction), expected_reduction
        ):
            qualifying.append(comparison)
    applies = candidate_exposure == 0.0 and bool(qualifying)
    displayed_reduction = (
        round(float(qualifying[0]["thermal_exposure_reduction_pct"])) if qualifying else None
    )
    return {
        "applies": applies,
        "message": (
            "Model-floor effect: ThermalShift reaches "
            f"{candidate_exposure:.3f} modeled stress-hours against small positive "
            f"baselines. This is not {displayed_reduction}% cooling, energy, electricity, "
            "water, or facility savings."
            if applies
            else None
        ),
    }


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceLoadError(f"Malformed {label} in committed evidence")
    return value


def _sequence(mapping: dict[str, Any], key: str) -> list[object]:
    value = mapping.get(key)
    if not isinstance(value, list):
        raise EvidenceLoadError(f"Missing or malformed {key} in committed evidence")
    return value


def _text(mapping: dict[str, Any], key: str) -> str:
    return _plain_text(mapping.get(key), key)


def _plain_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceLoadError(f"Missing or malformed {label} in committed evidence")
    return value


def _number(mapping: dict[str, Any], key: str) -> int | float:
    return _finite_number(mapping.get(key), key)


def _finite_number(value: object, label: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EvidenceLoadError(f"Missing or malformed {label} in committed evidence")
    if isinstance(value, float) and (value != value or abs(value) == float("inf")):
        raise EvidenceLoadError(f"Non-finite {label} in committed evidence")
    return value


def _boolean(mapping: dict[str, Any], key: str) -> bool:
    value = mapping.get(key)
    if not isinstance(value, bool):
        raise EvidenceLoadError(f"Missing or malformed {key} in committed evidence")
    return value
