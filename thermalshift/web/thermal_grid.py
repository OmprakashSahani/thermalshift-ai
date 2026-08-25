"""Sanitized historical thermal-grid export and strict public artifact loading."""

import json
import math
from datetime import UTC, datetime
from pathlib import Path

from thermalshift.domain.sites import get_default_sites
from thermalshift.fortyguard.cache import HeatmapResultCache
from thermalshift.replay.adapter import load_calibration_status, load_replay_observations
from thermalshift.replay.plan import get_replay_window
from thermalshift.scheduler.grid import ThermalGrid, ThermalGridEntry
from thermalshift.thermal.model import ThermalStressModel

SCHEMA_VERSION = "1.0"
CLASSIFICATION = "public_interactive_simulation_input"
BOUNDARY = (
    "FortyGuard historical ambient temperatures; modeled thermal-stress scores for "
    "interactive scheduling simulation."
)
SAFE_REQUEST_TIME_INTERPRETATION = (
    "AOI-local start_time; FortyGuard infers timezone and DST from the requested area; "
    "ThermalShift converts each orchestration UTC instant to modeled-site local time."
)
FORBIDDEN_KEYS = frozenset(
    {"api_key", "activity_id", "cache_key", "cache_path", "payload", "polygon", "map_data",
     "raw_fortyguard_response", "email", "environment_value"}
)


class ThermalGridArtifactError(RuntimeError):
    """Raised when a public thermal-grid artifact is missing or malformed."""


def export_thermal_grid(window_id: str, cache: HeatmapResultCache) -> dict[str, object]:
    """Build a deterministic sanitized artifact exclusively from complete cached data."""
    window = get_replay_window(window_id)
    calibration = load_calibration_status(cache)
    if not calibration.official_ready:
        raise ThermalGridArtifactError("Complete validated calibration cache is required")
    observations = load_replay_observations(window, cache)
    model = ThermalStressModel(calibration.lower_reference_c, calibration.upper_reference_c)
    entries = [
        {
            "site_id": observation.site_id,
            "timestamp_utc": (
                observation.timestamp.astimezone(UTC).isoformat().replace("+00:00", "Z")
            ),
            "temperature_c": observation.temperature_c,
            "thermal_stress_score": model.assess(observation).thermal_stress_score,
        }
        for observation in observations
    ]
    entries.sort(key=lambda item: (str(item["timestamp_utc"]), str(item["site_id"])))
    return {
        "schema_version": SCHEMA_VERSION,
        "window_id": window_id,
        "classification": CLASSIFICATION,
        "temperature_source": "fortyguard",
        "observation_type": "historical",
        "calibration_observation_count": 28,
        "calibration_rule": "pooled_p10_p90",
        "calibration_lower_reference_c": calibration.lower_reference_c,
        "calibration_upper_reference_c": calibration.upper_reference_c,
        "request_time_interpretation": SAFE_REQUEST_TIME_INTERPRETATION,
        "scientific_boundary": BOUNDARY,
        "entries": entries,
    }


def write_thermal_grid(artifact: dict[str, object], path: Path) -> None:
    """Write one deterministic, finite sanitized JSON artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True, allow_nan=False) + "\n")


def load_thermal_grid_artifact(
    evidence_root: Path, window_id: str
) -> tuple[dict[str, object], ThermalGrid]:
    """Strictly validate and reconstruct a scheduler grid for a known window."""
    window = get_replay_window(window_id)
    path = evidence_root / window_id / "thermal_grid.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        benchmark = json.loads((evidence_root / window_id / "benchmark.json").read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ThermalGridArtifactError(f"Thermal grid unavailable for {window_id}") from exc
    allowed_root_keys = {
        "schema_version", "window_id", "classification", "temperature_source",
        "observation_type", "calibration_observation_count", "calibration_rule",
        "calibration_lower_reference_c", "calibration_upper_reference_c",
        "request_time_interpretation", "scientific_boundary", "entries",
    }
    if not isinstance(raw, dict) or set(raw) != allowed_root_keys:
        raise ThermalGridArtifactError("Malformed or unsafe thermal grid artifact")
    expected = {
        "schema_version": SCHEMA_VERSION, "window_id": window_id,
        "classification": CLASSIFICATION, "temperature_source": "fortyguard",
        "observation_type": "historical", "calibration_observation_count": 28,
        "calibration_rule": "pooled_p10_p90",
        "request_time_interpretation": SAFE_REQUEST_TIME_INTERPRETATION,
        "scientific_boundary": BOUNDARY,
    }
    if any(raw.get(key) != value for key, value in expected.items()):
        raise ThermalGridArtifactError("Thermal grid provenance is invalid")
    provenance = benchmark.get("provenance", {})
    for key in ("calibration_lower_reference_c", "calibration_upper_reference_c"):
        value = raw.get(key)
        if not _finite(value) or value != provenance.get(key):
            raise ThermalGridArtifactError("Calibration references do not match committed evidence")
    entries = raw.get("entries")
    if not isinstance(entries, list) or len(entries) != 24:
        raise ThermalGridArtifactError("Thermal grid must contain exactly 24 entries")
    ordering = [
        (item.get("timestamp_utc"), item.get("site_id"))
        for item in entries
        if isinstance(item, dict)
    ]
    if len(ordering) != 24 or ordering != sorted(ordering):
        raise ThermalGridArtifactError("Thermal grid entries are not deterministically ordered")
    expected_sites = {site.site_id for site in get_default_sites()}
    expected_times = {instant.isoformat().replace("+00:00", "Z") for instant in window.instants}
    pairs: set[tuple[str, str]] = set()
    grid_entries = []
    allowed_entry_keys = {"site_id", "timestamp_utc", "temperature_c", "thermal_stress_score"}
    for item in entries:
        if not isinstance(item, dict) or set(item) != allowed_entry_keys:
            raise ThermalGridArtifactError("Thermal grid entry fields are invalid")
        site_id, timestamp = item["site_id"], item["timestamp_utc"]
        score, temperature = item["thermal_stress_score"], item["temperature_c"]
        if site_id not in expected_sites or timestamp not in expected_times:
            raise ThermalGridArtifactError("Thermal grid site or timestamp is invalid")
        if not _finite(temperature) or not _finite(score) or not 0 <= score <= 1:
            raise ThermalGridArtifactError("Thermal grid values are invalid")
        pair = (site_id, timestamp)
        if pair in pairs:
            raise ThermalGridArtifactError("Duplicate thermal grid site/hour")
        pairs.add(pair)
        parsed_timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        grid_entries.append(ThermalGridEntry(site_id, parsed_timestamp, score))
    if (
        {site for site, _ in pairs} != expected_sites
        or {time for _, time in pairs} != expected_times
    ):
        raise ThermalGridArtifactError("Thermal grid coverage is incomplete")
    return raw, ThermalGrid(grid_entries)


def _finite(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
