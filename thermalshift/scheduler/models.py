"""Immutable scheduling abstractions shared by all scheduler policies."""

from dataclasses import dataclass
from datetime import datetime

from thermalshift.domain.models import ScheduleDecision, Site, Workload


@dataclass(frozen=True, slots=True)
class PlacementCandidate:
    """One operationally valid workload placement before shared capacity checks."""

    workload: Workload
    site: Site
    site_order: int
    start_time: datetime
    end_time: datetime
    occupied_timestamps: tuple[datetime, ...]
    thermal_scores: tuple[float, ...]
    thermal_exposure: float
    thermal_stress_avg: float


@dataclass(frozen=True, slots=True)
class SchedulingResult:
    """Placed decisions and explicit unscheduled workloads from one scheduler."""

    scheduler_name: str
    decisions: tuple[ScheduleDecision, ...]
    unscheduled_workload_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        decision_ids = [decision.workload_id for decision in self.decisions]
        if len(decision_ids) != len(set(decision_ids)):
            raise ValueError("A workload may have at most one schedule decision")
        if tuple(decision_ids) != tuple(sorted(decision_ids)):
            raise ValueError("Schedule decisions must be ordered by workload ID")
        if self.unscheduled_workload_ids != tuple(sorted(self.unscheduled_workload_ids)):
            raise ValueError("Unscheduled workload IDs must be sorted")
        if set(decision_ids) & set(self.unscheduled_workload_ids):
            raise ValueError("A workload cannot be both scheduled and unscheduled")

    @property
    def scheduled_count(self) -> int:
        """Return the number of successfully placed workloads."""
        return len(self.decisions)

    @property
    def unscheduled_count(self) -> int:
        """Return the number of workloads without a placement."""
        return len(self.unscheduled_workload_ids)
