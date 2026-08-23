"""Shared deterministic candidate generation and capacity accounting."""

from collections.abc import Iterable, Sequence
from datetime import UTC, datetime, timedelta

from thermalshift.domain.models import ScheduleDecision, Site, Workload
from thermalshift.scheduler.grid import ThermalGrid
from thermalshift.scheduler.models import PlacementCandidate, SchedulingResult

CapacityLedger = dict[tuple[str, datetime], int]


class SchedulingInputError(ValueError):
    """Raised when scheduler inputs contain duplicate stable identifiers."""


def prepare_inputs(
    sites: Iterable[Site], workloads: Iterable[Workload]
) -> tuple[tuple[Site, ...], tuple[Workload, ...]]:
    """Validate IDs and return sites plus workloads in shared stable order."""
    site_values = tuple(sites)
    workload_values = tuple(workloads)
    _reject_duplicate_ids((site.site_id for site in site_values), "site")
    _reject_duplicate_ids((workload.workload_id for workload in workload_values), "workload")
    ordered_workloads = tuple(
        sorted(
            workload_values,
            key=lambda workload: (
                workload.release_time.astimezone(UTC),
                workload.deadline.astimezone(UTC),
                workload.workload_id,
            ),
        )
    )
    return site_values, ordered_workloads


def candidates_for_workload(
    workload: Workload, sites: Sequence[Site], grid: ThermalGrid
) -> tuple[PlacementCandidate, ...]:
    """Generate candidates satisfying individual operational constraints."""
    release_utc = workload.release_time.astimezone(UTC)
    deadline_utc = workload.deadline.astimezone(UTC)
    candidates: list[PlacementCandidate] = []
    for site_order, site in enumerate(sites):
        if site.site_id not in workload.eligible_site_ids:
            continue
        if workload.gpu_demand > site.total_gpu_capacity:
            continue
        for start_time in grid.available_timestamps(site.site_id):
            end_time = start_time + timedelta(hours=workload.duration_hours)
            if start_time < release_utc or end_time > deadline_utc:
                continue
            metrics = grid.placement_metrics(
                site.site_id, start_time, workload.duration_hours
            )
            if metrics is None:
                continue
            occupied = tuple(
                start_time + timedelta(hours=offset)
                for offset in range(workload.duration_hours)
            )
            candidates.append(
                PlacementCandidate(
                    workload=workload,
                    site=site,
                    site_order=site_order,
                    start_time=start_time,
                    end_time=end_time,
                    occupied_timestamps=occupied,
                    thermal_scores=metrics.scores,
                    thermal_exposure=metrics.exposure_stress_hours,
                    thermal_stress_avg=metrics.average_stress,
                )
            )
    return tuple(
        sorted(candidates, key=lambda candidate: (candidate.start_time, candidate.site_order))
    )


def has_capacity(candidate: PlacementCandidate, ledger: CapacityLedger) -> bool:
    """Return whether shared site/hour capacity admits the candidate."""
    return all(
        ledger.get((candidate.site.site_id, timestamp), 0) + candidate.workload.gpu_demand
        <= candidate.site.total_gpu_capacity
        for timestamp in candidate.occupied_timestamps
    )


def minimum_residual_capacity(candidate: PlacementCandidate, ledger: CapacityLedger) -> int:
    """Return the smallest remaining capacity if the candidate is reserved."""
    return min(
        candidate.site.total_gpu_capacity
        - ledger.get((candidate.site.site_id, timestamp), 0)
        - candidate.workload.gpu_demand
        for timestamp in candidate.occupied_timestamps
    )


def reserve(candidate: PlacementCandidate, ledger: CapacityLedger) -> None:
    """Reserve a candidate's GPU demand in every occupied site/hour."""
    for timestamp in candidate.occupied_timestamps:
        key = (candidate.site.site_id, timestamp)
        ledger[key] = ledger.get(key, 0) + candidate.workload.gpu_demand


def build_result(
    scheduler_name: str,
    workloads: Sequence[Workload],
    selected: Sequence[PlacementCandidate],
    decision_reason: str,
) -> SchedulingResult:
    """Convert placements into deterministically ordered schedule decisions."""
    decisions = tuple(
        sorted(
            (
                ScheduleDecision(
                    workload_id=candidate.workload.workload_id,
                    site_id=candidate.site.site_id,
                    start_time=candidate.start_time,
                    end_time=candidate.end_time,
                    thermal_exposure=candidate.thermal_exposure,
                    thermal_stress_avg=candidate.thermal_stress_avg,
                    deadline_satisfied=True,
                    capacity_satisfied=True,
                    scheduler_name=scheduler_name,
                    decision_reason=decision_reason,
                )
                for candidate in selected
            ),
            key=lambda decision: decision.workload_id,
        )
    )
    selected_ids = {candidate.workload.workload_id for candidate in selected}
    unscheduled = tuple(
        sorted(
            workload.workload_id
            for workload in workloads
            if workload.workload_id not in selected_ids
        )
    )
    return SchedulingResult(scheduler_name, decisions, unscheduled)


def _reject_duplicate_ids(values: Iterable[str], entity: str) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise SchedulingInputError(f"duplicate {entity} ID: {value}")
        seen.add(value)
