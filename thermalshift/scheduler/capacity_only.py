"""Deterministic temperature-unaware capacity-balancing baseline."""

from collections.abc import Iterable

from thermalshift.domain.models import Site, Workload
from thermalshift.scheduler.common import (
    CapacityLedger,
    build_result,
    candidates_for_workload,
    has_capacity,
    minimum_residual_capacity,
    prepare_inputs,
    reserve,
)
from thermalshift.scheduler.grid import ThermalGrid
from thermalshift.scheduler.models import PlacementCandidate, SchedulingResult

SCHEDULER_NAME = "capacity_only"


def schedule(
    sites: Iterable[Site], workloads: Iterable[Workload], grid: ThermalGrid
) -> SchedulingResult:
    """Maximize minimum residual capacity, then prefer earlier time and site order."""
    site_values, workload_values = prepare_inputs(sites, workloads)
    ledger: CapacityLedger = {}
    selected: list[PlacementCandidate] = []
    for workload in workload_values:
        feasible = [
            candidate
            for candidate in candidates_for_workload(workload, site_values, grid)
            if has_capacity(candidate, ledger)
        ]
        if not feasible:
            continue
        candidate = min(
            feasible,
            key=lambda option: (
                -minimum_residual_capacity(option, ledger),
                option.start_time,
                option.site_order,
            ),
        )
        reserve(candidate, ledger)
        selected.append(candidate)
    return build_result(
        SCHEDULER_NAME,
        workload_values,
        selected,
        "Largest minimum residual GPU capacity; temperature not used for selection.",
    )
