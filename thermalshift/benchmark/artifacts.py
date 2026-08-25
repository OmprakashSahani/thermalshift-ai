"""Deterministic, evidence-qualified benchmark artifacts."""

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from thermalshift.domain.models import ScheduleDecision, Site, Workload

from .comparison import format_headline, thermalshift_comparisons
from .models import BenchmarkMetrics, BenchmarkReport, BenchmarkScenario

ARTIFACT_SCHEMA_VERSION = "1.0"
REQUEST_TIME_INTERPRETATION = (
    "AOI-local start_time; FortyGuard infers timezone and DST from AOI polygon "
    "coordinates; ThermalShift converts each orchestration UTC instant to the modeled "
    "site local time before submission"
)
MODELED_METRIC_BOUNDARY = (
    "Thermal stress-hours are a modeled scheduling metric derived from ambient-temperature inputs."
)
NOT_MEASURED_BOUNDARIES = (
    "GPU temperature",
    "server inlet temperature",
    "PUE",
    "cooling energy",
    "electricity consumption",
    "electricity savings",
    "water consumption",
    "water savings",
)

EvidenceType = Literal["synthetic_demonstration", "fortyguard_historical_replay"]


@dataclass(frozen=True, slots=True)
class HistoricalProvenance:
    """Provenance required for a complete FortyGuard historical replay."""

    replay_window_id: str
    replay_start_utc: datetime
    replay_slot_count: int
    calibration_observation_count: int
    calibration_lower_reference_c: float
    calibration_upper_reference_c: float
    calibration_rule: str = "pooled_p10_p90"
    temperature_source: str = "fortyguard"
    workload_source: str = "modeled"
    site_capacity_source: str = "modeled"
    request_time_interpretation: str = REQUEST_TIME_INTERPRETATION


@dataclass(frozen=True, slots=True)
class BenchmarkArtifact:
    """Complete serializable evidence record for one benchmark report."""

    artifact_schema_version: str
    scenario_id: str
    scenario_description: str
    data_source_label: str
    evidence_type: EvidenceType
    generated_at_utc: datetime | None
    sites: tuple[dict[str, object], ...]
    workloads: tuple[dict[str, object], ...]
    scheduler_runs: tuple[dict[str, object], ...]
    comparisons: tuple[dict[str, object], ...]
    provenance: HistoricalProvenance | None
    evidence_boundaries: dict[str, object]


def build_benchmark_artifact(
    scenario: BenchmarkScenario,
    report: BenchmarkReport,
    *,
    evidence_type: EvidenceType,
    generated_at_utc: datetime | None = None,
    provenance: HistoricalProvenance | None = None,
) -> BenchmarkArtifact:
    """Build an artifact from existing scenario, report, and comparison logic."""
    if report.scenario_id != scenario.scenario_id:
        raise ValueError("scenario and report IDs must match")
    if generated_at_utc is not None:
        _require_aware(generated_at_utc, "generated_at_utc")
    if evidence_type == "fortyguard_historical_replay" and provenance is None:
        raise ValueError("historical replay artifacts require provenance")
    if evidence_type == "synthetic_demonstration" and provenance is not None:
        raise ValueError("synthetic artifacts must not include historical provenance")

    comparisons = thermalshift_comparisons(report)
    return BenchmarkArtifact(
        artifact_schema_version=ARTIFACT_SCHEMA_VERSION,
        scenario_id=report.scenario_id,
        scenario_description=report.description,
        data_source_label=report.data_source_label,
        evidence_type=evidence_type,
        generated_at_utc=generated_at_utc,
        sites=tuple(
            _serialize_site(site) for site in sorted(scenario.sites, key=lambda x: x.site_id)
        ),
        workloads=tuple(
            _serialize_workload(workload)
            for workload in sorted(scenario.workloads, key=lambda x: x.workload_id)
        ),
        scheduler_runs=tuple(
            _serialize_run(run.metrics, run.result.decisions) for run in report.runs
        ),
        comparisons=tuple(
            {
                "baseline_scheduler": item.baseline_scheduler,
                "candidate_scheduler": item.candidate_scheduler,
                "same_scheduled_workload_set": item.same_scheduled_workload_set,
                "completion_preserved": item.completion_preserved,
                "deadline_satisfaction_preserved": item.deadline_satisfaction_preserved,
                "direct_thermal_comparison_valid": item.direct_thermal_comparison_valid,
                "thermal_exposure_delta_stress_hours": item.thermal_exposure_delta_stress_hours,
                "thermal_exposure_reduction_pct": item.thermal_exposure_reduction_pct,
                "headline": format_headline(item),
            }
            for item in comparisons
        ),
        provenance=provenance,
        evidence_boundaries=_evidence_boundaries(evidence_type),
    )


def write_benchmark_json(artifact: BenchmarkArtifact, path: Path) -> None:
    """Write stable UTF-8 JSON, rejecting non-finite numeric values."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(
        benchmark_artifact_dict(artifact),
        allow_nan=False,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    path.write_text(f"{rendered}\n", encoding="utf-8")


def render_benchmark_markdown(artifact: BenchmarkArtifact) -> str:
    """Render a compact judge-facing report from an artifact."""
    historical = artifact.evidence_type == "fortyguard_historical_replay"
    classification = (
        "FORTYGUARD-BACKED HISTORICAL REPLAY\n\n"
        "REAL HISTORICAL AMBIENT TEMPERATURES + MODELED WORKLOADS"
        if historical
        else "SYNTHETIC DEMONSTRATION — NOT FORTYGUARD BENCHMARK EVIDENCE"
    )
    generated_at = _iso(artifact.generated_at_utc) if artifact.generated_at_utc else "not supplied"
    lines = [
        "# ThermalShift Benchmark Report",
        "",
        "## Evidence classification",
        "",
        classification,
        "",
        "## Scenario",
        "",
        f"- Scenario ID: `{artifact.scenario_id}`",
        f"- Description: {artifact.scenario_description}",
        f"- Data source: `{artifact.data_source_label}`",
        f"- Generated at UTC: {generated_at}",
        "",
        "## Calibration / provenance",
        "",
    ]
    if artifact.provenance is None:
        lines.append("Not applicable: all thermal scores are synthetic demonstration inputs.")
    else:
        provenance = artifact.provenance
        lines.extend(
            (
                f"- Replay window: `{provenance.replay_window_id}` starting "
                f"{_iso(provenance.replay_start_utc)}",
                f"- Replay slots: {provenance.replay_slot_count}",
                f"- Calibration: {provenance.calibration_observation_count} "
                f"observations; `{provenance.calibration_rule}`",
                f"- Calibration references: "
                f"{provenance.calibration_lower_reference_c}°C / "
                f"{provenance.calibration_upper_reference_c}°C",
                f"- Request-time interpretation: {provenance.request_time_interpretation}",
            )
        )
    lines.extend(("", "## Scheduler results", "", _scheduler_table(artifact), ""))
    lines.extend(("## ThermalShift comparisons", ""))
    for comparison in artifact.comparisons:
        baseline_name = str(comparison["baseline_scheduler"]).replace("_", " ").title()
        lines.append(f"- **ThermalShift vs {baseline_name}:** {comparison['headline']}")
    zero_floor_note = _historical_zero_floor_note(artifact)
    if zero_floor_note is not None:
        lines.extend(("", zero_floor_note))
    lines.extend(("", "## Scheduling decisions", ""))
    for run in artifact.scheduler_runs:
        lines.extend((f"### {run['scheduler_name']}", ""))
        decisions = run["decisions"]
        if not decisions:
            lines.append("No workloads scheduled.")
        else:
            lines.extend(
                (
                    "| Workload | Site | Start | End | Exposure | Mean stress | "
                    "Deadline | Capacity | Reason |",
                    "|---|---|---|---|---:|---:|:---:|:---:|---|",
                )
            )
            for decision in decisions:
                lines.append(
                    f"| {decision['workload_id']} | {decision['site_id']} | "
                    f"{decision['start_time']} | "
                    f"{decision['end_time']} | {decision['thermal_exposure']} | "
                    f"{decision['thermal_stress_avg']} | {decision['deadline_satisfied']} | "
                    f"{decision['capacity_satisfied']} | {decision['decision_reason'] or ''} |"
                )
        lines.append("")
    lines.extend(
        (
            "## Methodology and fairness",
            "",
            "All schedulers receive the same sites, workloads, capacity constraints, "
            "and thermal grid. Direct thermal percentages use the existing fairness "
            "gate and are available only when scheduled workload sets match.",
            "",
            "## Scientific boundaries",
            "",
            f"{MODELED_METRIC_BOUNDARY} They are not " + ", ".join(NOT_MEASURED_BOUNDARIES) + ".",
            "",
            str(artifact.evidence_boundaries["evidence_classification"]),
            "",
            "## Reproducibility",
            "",
            f"Artifact schema: `{artifact.artifact_schema_version}`. Sites and workloads "
            "are ID-sorted; scenario inputs, scheduler decisions, thermal metrics, and "
            "fairness comparisons are deterministic for identical inputs. JSON structure "
            "and key ordering are stable. Measured `runtime_ms` is observational and may "
            "vary by machine or execution; `generated_at_utc`, when supplied, is metadata.",
            "",
        )
    )
    return "\n".join(lines)


def write_benchmark_markdown(artifact: BenchmarkArtifact, path: Path) -> None:
    """Write deterministic UTF-8 Markdown with a newline at EOF."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_benchmark_markdown(artifact), encoding="utf-8")


def write_benchmark_artifacts(artifact: BenchmarkArtifact, output_dir: Path) -> tuple[Path, Path]:
    """Create an output directory and write the standard JSON and Markdown files."""
    json_path = output_dir / "benchmark.json"
    markdown_path = output_dir / "report.md"
    write_benchmark_json(artifact, json_path)
    write_benchmark_markdown(artifact, markdown_path)
    return json_path, markdown_path


def benchmark_artifact_dict(artifact: BenchmarkArtifact) -> dict[str, object]:
    """Return a JSON-compatible artifact mapping with ISO 8601 datetimes."""
    return _json_value(asdict(artifact))


def _serialize_site(site: Site) -> dict[str, object]:
    return {
        "site_id": site.site_id,
        "name": site.name,
        "latitude": site.latitude,
        "longitude": site.longitude,
        "timezone": site.timezone,
        "modeled_gpu_capacity": site.total_gpu_capacity,
    }


def _serialize_workload(workload: Workload) -> dict[str, object]:
    return {
        "workload_id": workload.workload_id,
        "name": workload.name,
        "gpu_demand": workload.gpu_demand,
        "duration_hours": workload.duration_hours,
        "release_time": _iso(workload.release_time),
        "deadline": _iso(workload.deadline),
        "priority": workload.priority.value,
        "eligible_site_ids": sorted(workload.eligible_site_ids),
    }


def _serialize_run(
    metrics: BenchmarkMetrics, decisions: tuple[ScheduleDecision, ...]
) -> dict[str, object]:
    return {
        "scheduler_name": metrics.scheduler_name,
        "total_workloads": metrics.total_workloads,
        "scheduled_count": metrics.scheduled_count,
        "unscheduled_count": metrics.unscheduled_count,
        "completion_rate": metrics.completion_rate,
        "deadline_satisfaction_count": metrics.deadline_satisfied_count,
        "deadline_satisfaction_rate": metrics.deadline_satisfaction_rate,
        "scheduled_workload_ids": list(metrics.scheduled_workload_ids),
        "unscheduled_workload_ids": sorted(metrics.unscheduled_workload_ids),
        "total_scheduled_workload_hours": metrics.total_scheduled_workload_hours,
        "total_thermal_exposure_stress_hours": metrics.total_thermal_exposure_stress_hours,
        "mean_thermal_exposure_per_scheduled_workload": (
            metrics.mean_thermal_exposure_per_scheduled_workload
        ),
        "mean_occupied_thermal_stress": metrics.mean_occupied_thermal_stress,
        "peak_occupied_thermal_stress": metrics.peak_occupied_thermal_stress,
        "runtime_ms": metrics.runtime_ms,
        "decisions": [_serialize_decision(decision) for decision in decisions],
    }


def _serialize_decision(decision: ScheduleDecision) -> dict[str, object]:
    return {
        "workload_id": decision.workload_id,
        "site_id": decision.site_id,
        "start_time": _iso(decision.start_time),
        "end_time": _iso(decision.end_time),
        "thermal_exposure": decision.thermal_exposure,
        "thermal_stress_avg": decision.thermal_stress_avg,
        "deadline_satisfied": decision.deadline_satisfied,
        "capacity_satisfied": decision.capacity_satisfied,
        "scheduler_name": decision.scheduler_name,
        "decision_reason": decision.decision_reason,
    }


def _evidence_boundaries(evidence_type: EvidenceType) -> dict[str, object]:
    classification = (
        "Ambient temperatures come from FortyGuard; workloads and GPU capacities "
        "are modeled benchmark parameters, not real customer workloads or facility telemetry."
        if evidence_type == "fortyguard_historical_replay"
        else "Thermal scores are synthetic demonstration inputs and are not FortyGuard evidence."
    )
    return {
        "thermal_stress_hours": MODELED_METRIC_BOUNDARY,
        "not_measured_or_proven": list(NOT_MEASURED_BOUNDARIES),
        "evidence_classification": classification,
    }


def _scheduler_table(artifact: BenchmarkArtifact) -> str:
    lines = [
        "| Scheduler | Scheduled | Unscheduled | Completion | Deadline satisfaction | "
        "Stress-hours | Mean occupied stress | Peak occupied stress | Runtime ms |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for run in artifact.scheduler_runs:
        lines.append(
            f"| {run['scheduler_name']} | {run['scheduled_count']} | {run['unscheduled_count']} | "
            f"{100 * float(run['completion_rate']):.1f}% | "
            f"{100 * float(run['deadline_satisfaction_rate']):.1f}% | "
            f"{float(run['total_thermal_exposure_stress_hours']):.3f} | "
            f"{float(run['mean_occupied_thermal_stress']):.3f} | "
            f"{float(run['peak_occupied_thermal_stress']):.3f} | {float(run['runtime_ms']):.3f} |"
        )
    return "\n".join(lines)


def _historical_zero_floor_note(artifact: BenchmarkArtifact) -> str | None:
    if artifact.evidence_type != "fortyguard_historical_replay":
        return None

    runs = {str(run["scheduler_name"]): run for run in artifact.scheduler_runs}
    candidate = runs.get("thermalshift")
    if candidate is None or float(candidate["total_thermal_exposure_stress_hours"]) != 0.0:
        return None

    qualifying_baselines = []
    for comparison in artifact.comparisons:
        baseline_name = str(comparison["baseline_scheduler"])
        baseline = runs.get(baseline_name)
        reduction = comparison["thermal_exposure_reduction_pct"]
        if (
            comparison["direct_thermal_comparison_valid"] is True
            and baseline is not None
            and float(baseline["total_thermal_exposure_stress_hours"]) > 0.0
            and reduction is not None
            and round(float(reduction), 1) == 100.0
        ):
            display_name = baseline_name.replace("_", " ").title()
            exposure = float(baseline["total_thermal_exposure_stress_hours"])
            qualifying_baselines.append(f"{display_name}: {exposure:.3f}")

    if not qualifying_baselines:
        return None

    baseline_summary = "; ".join(qualifying_baselines)
    return (
        "**Interpretation note:** ThermalShift reaches the modeled thermal-stress floor in "
        "this replay. The 100% relative reduction means candidate stress-hours are 0.000 "
        f"against positive baseline stress-hours ({baseline_summary}); it does not mean 100% "
        "cooling, energy, electricity, water, or facility savings."
    )


def _json_value(value):
    if isinstance(value, datetime):
        return _iso(value)
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
