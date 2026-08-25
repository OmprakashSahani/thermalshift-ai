"""Bounded live Scenario Lab service using the production scheduler suite."""

from datetime import timedelta
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from thermalshift.benchmark.comparison import thermalshift_comparisons
from thermalshift.benchmark.models import BenchmarkScenario
from thermalshift.benchmark.runner import run_benchmark
from thermalshift.domain.models import Workload, WorkloadPriority
from thermalshift.domain.sites import get_default_sites
from thermalshift.replay.adapter import HISTORICAL_DATA_SOURCE_LABEL
from thermalshift.replay.plan import get_replay_window
from thermalshift.replay.workloads import build_replay_workloads
from thermalshift.scheduler.common import candidates_for_workload

from .thermal_grid import load_thermal_grid_artifact

SITE_IDS = tuple(site.site_id for site in get_default_sites())
STATEMENT = (
    "Interactive results use real FortyGuard historical ambient conditions with modeled "
    "workload/capacity inputs. They are simulation results, not the committed hackathon benchmark."
)


class ScenarioRequest(BaseModel):
    """Exactly one bounded modeled workload for a predeclared replay window."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    window_id: Literal["summer-midday-v1", "winter-overnight-v1"]
    gpu_demand: int = Field(strict=True, ge=1, le=64)
    duration_hours: int = Field(strict=True, ge=1, le=3)
    release_offset_hours: int = Field(strict=True, ge=0, le=4)
    deadline_offset_hours: int = Field(strict=True, ge=1, le=6)
    eligible_site_ids: list[Literal[
        "ashburn-va", "phoenix-az", "san-antonio-tx", "atlanta-ga"
    ]] = Field(min_length=1, max_length=4)

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        if len(self.eligible_site_ids) != len(set(self.eligible_site_ids)):
            raise ValueError("eligible_site_ids must not contain duplicates")
        available = self.deadline_offset_hours - self.release_offset_hours
        if available <= 0:
            raise ValueError("deadline_offset_hours must be greater than release_offset_hours")
        if self.duration_hours > available:
            raise ValueError("duration_hours must fit between release and deadline")
        return self


def run_scenario(request: ScenarioRequest, evidence_root: Path) -> dict[str, object]:
    """Append `whatif` and run the existing benchmark scheduler suite at request time."""
    window = get_replay_window(request.window_id)
    artifact, grid = load_thermal_grid_artifact(evidence_root, request.window_id)
    workload = Workload(
        workload_id="whatif",
        name="Scenario Lab user-defined workload",
        gpu_demand=request.gpu_demand,
        duration_hours=request.duration_hours,
        release_time=window.start_utc + timedelta(hours=request.release_offset_hours),
        deadline=window.start_utc + timedelta(hours=request.deadline_offset_hours),
        priority=WorkloadPriority.MEDIUM,
        eligible_site_ids=frozenset(request.eligible_site_ids),
    )
    sites = get_default_sites()
    scenario = BenchmarkScenario(
        scenario_id=f"interactive-{window.window_id}",
        description=STATEMENT,
        sites=sites,
        workloads=build_replay_workloads(window) + (workload,),
        thermal_grid=grid,
        data_source_label=HISTORICAL_DATA_SOURCE_LABEL,
    )
    report = run_benchmark(scenario)
    comparisons = thermalshift_comparisons(report)
    return {
        "classification": "interactive_simulation",
        "official_benchmark_evidence": False,
        "statement": STATEMENT,
        "window": {
            "window_id": window.window_id,
            "start_utc": _iso(window.start_utc),
            "hourly_timestamps_utc": [_iso(item) for item in window.instants],
        },
        "user_workload": {
            **request.model_dump(),
            "workload_id": "whatif",
            "priority": "medium (fixed)",
            "release_time_utc": _iso(workload.release_time),
            "deadline_utc": _iso(workload.deadline),
        },
        "schedulers": [_run_dict(run) for run in report.runs],
        "comparisons": [
            {
                "baseline_scheduler": item.baseline_scheduler,
                "candidate_scheduler": item.candidate_scheduler,
                "same_scheduled_workload_set": item.same_scheduled_workload_set,
                "direct_thermal_comparison_valid": item.direct_thermal_comparison_valid,
                "thermal_exposure_reduction_pct": item.thermal_exposure_reduction_pct,
                "completion_preserved": item.completion_preserved,
                "deadline_satisfaction_preserved": item.deadline_satisfaction_preserved,
            }
            for item in comparisons
        ],
        "comparison_boundary": (
            "Percentages compare modeled ambient thermal exposure only when scheduled "
            "workload sets match. They are not cooling, energy, electricity, water, PUE, "
            "or facility-savings percentages; model-floor results require particular care."
        ),
        "candidate_placements": [
            {
                "site_id": candidate.site.site_id,
                "start_utc": _iso(candidate.start_time),
                "end_utc": _iso(candidate.end_time),
                "thermal_exposure": candidate.thermal_exposure,
                "mean_modeled_stress": candidate.thermal_stress_avg,
            }
            for candidate in candidates_for_workload(workload, sites, grid)
        ],
        "thermal_landscape": artifact["entries"],
        "candidate_note": (
            "Candidates satisfy individual constraints before aggregate capacity interactions; "
            "the final scheduler choice also reflects shared capacity."
        ),
    }


def _run_dict(run) -> dict[str, object]:
    metrics = run.metrics
    decision = next((item for item in run.result.decisions if item.workload_id == "whatif"), None)
    custom = (
        {
            "status": "scheduled", "site_id": decision.site_id,
            "start_utc": _iso(decision.start_time), "end_utc": _iso(decision.end_time),
            "thermal_exposure": decision.thermal_exposure,
            "mean_modeled_stress": decision.thermal_stress_avg,
            "deadline_satisfied": decision.deadline_satisfied,
            "capacity_satisfied": decision.capacity_satisfied,
        }
        if decision
        else {"status": "unscheduled", "reason": "No aggregate-capacity-feasible placement."}
    )
    return {
        "scheduler_name": metrics.scheduler_name,
        "scheduled_count": metrics.scheduled_count,
        "total_workload_count": metrics.total_workloads,
        "completion_rate": metrics.completion_rate,
        "deadline_satisfaction_rate": metrics.deadline_satisfaction_rate,
        "total_thermal_exposure_stress_hours": metrics.total_thermal_exposure_stress_hours,
        "scheduled_workload_ids": list(metrics.scheduled_workload_ids),
        "whatif": custom,
    }


def _iso(value) -> str:
    return value.isoformat().replace("+00:00", "Z")
