"""Deterministic temperature-unaware First Available baseline."""

from collections.abc import Iterable

from thermalshift.domain.models import Site, Workload
from thermalshift.scheduler.common import (
    CapacityLedger,
    build_result,
    candidates_for_workload,
    has_capacity,
    prepare_inputs,
    reserve,
)
from thermalshift.scheduler.grid import ThermalGrid
from thermalshift.scheduler.models import PlacementCandidate, SchedulingResult

SCHEDULER_NAME = "first_available"


def schedule(
    sites: Iterable[Site], workloads: Iterable[Workload], grid: ThermalGrid
) -> SchedulingResult:
    """Choose each workload's earliest feasible start, then site sequence order."""
    site_values, workload_values = prepare_inputs(sites, workloads)
    ledger: CapacityLedger = {}
    selected: list[PlacementCandidate] = []
    for workload in workload_values:
        candidate = next(
            (
                option
                for option in candidates_for_workload(workload, site_values, grid)
                if has_capacity(option, ledger)
            ),
            None,
        )
        if candidate is not None:
            reserve(candidate, ledger)
            selected.append(candidate)
    return build_result(
        SCHEDULER_NAME,
        workload_values,
        selected,
        "Earliest feasible placement using stable site order; temperature not used for selection.",
    )
