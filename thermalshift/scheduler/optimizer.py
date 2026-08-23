"""Completion-first ThermalShift CP-SAT scheduler."""

from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime

from ortools.sat.python import cp_model

from thermalshift.domain.models import Site, Workload
from thermalshift.scheduler.common import build_result, candidates_for_workload, prepare_inputs
from thermalshift.scheduler.grid import ThermalGrid
from thermalshift.scheduler.models import SchedulingResult

SCHEDULER_NAME = "thermalshift"
THERMAL_OBJECTIVE_SCALE = 1_000_000


class ThermalShiftSolverError(RuntimeError):
    """Raised when CP-SAT cannot prove an expected optimization phase."""


def schedule(
    sites: Iterable[Site], workloads: Iterable[Workload], grid: ThermalGrid
) -> SchedulingResult:
    """Maximize completion, then minimize exposure, then deterministic rank."""
    site_values, workload_values = prepare_inputs(sites, workloads)
    candidates = tuple(
        candidate
        for workload in workload_values
        for candidate in candidates_for_workload(workload, site_values, grid)
    )
    if not candidates:
        return build_result(SCHEDULER_NAME, workload_values, (), _DECISION_REASON)

    model = cp_model.CpModel()
    variables = [model.new_bool_var(f"placement_{index}") for index in range(len(candidates))]
    by_workload: dict[str, list[int]] = defaultdict(list)
    by_site_hour: dict[tuple[str, datetime], list[int]] = defaultdict(list)
    for index, candidate in enumerate(candidates):
        by_workload[candidate.workload.workload_id].append(index)
        for timestamp in candidate.occupied_timestamps:
            by_site_hour[(candidate.site.site_id, timestamp)].append(index)

    for indexes in by_workload.values():
        model.add(sum(variables[index] for index in indexes) <= 1)
    site_capacities = {site.site_id: site.total_gpu_capacity for site in site_values}
    for (site_id, _timestamp), indexes in by_site_hour.items():
        model.add(
            sum(candidates[index].workload.gpu_demand * variables[index] for index in indexes)
            <= site_capacities[site_id]
        )

    completion = sum(variables)
    model.maximize(completion)
    solver = _new_solver()
    _require_optimal(solver.solve(model), "completion maximization")
    maximum_completion = sum(solver.value(variable) for variable in variables)
    model.add(completion == maximum_completion)

    scaled_exposures = [
        round(candidate.thermal_exposure * THERMAL_OBJECTIVE_SCALE)
        for candidate in candidates
    ]
    thermal_objective = sum(
        scaled_exposures[index] * variables[index] for index in range(len(candidates))
    )
    model.minimize(thermal_objective)
    solver = _new_solver()
    _require_optimal(solver.solve(model), "thermal exposure minimization")
    minimum_thermal_exposure = sum(
        scaled_exposures[index] * solver.value(variables[index])
        for index in range(len(candidates))
    )
    model.add(thermal_objective == minimum_thermal_exposure)

    model.minimize(
        sum((index + 1) * variables[index] for index in range(len(candidates)))
    )
    solver = _new_solver()
    _require_optimal(solver.solve(model), "deterministic placement tie-break")
    selected = tuple(
        candidate
        for index, candidate in enumerate(candidates)
        if solver.value(variables[index])
    )
    return build_result(
        SCHEDULER_NAME, workload_values, selected, _DECISION_REASON
    )


def _new_solver() -> cp_model.CpSolver:
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0
    return solver


def _require_optimal(status: cp_model.CpSolverStatus, phase: str) -> None:
    if status != cp_model.OPTIMAL:
        raise ThermalShiftSolverError(f"CP-SAT did not prove optimality during {phase}: {status}")


_DECISION_REASON = (
    "Constraint-aware thermal optimization after preserving maximum feasible workload completion."
)
