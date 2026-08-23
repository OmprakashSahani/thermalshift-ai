# Scheduling model

ThermalShift's MVP uses one-hour candidate start times and one-hour thermal-grid intervals. Domain
datetimes remain timezone-aware, while scheduling keys and comparisons normalize equivalent
instants to UTC. A candidate exists only when its modeled site is eligible, its GPU demand fits the
site, its start/runtime/end lie within release and deadline constraints, and every occupied hourly
thermal-grid slot exists. Missing thermal data makes that placement unavailable.

For every site and hour, aggregate demand from selected overlapping placements must not exceed the
modeled GPU capacity. Successful decisions therefore have satisfied deadline and capacity flags.

## Policies

- **First Available** processes workloads by release UTC, deadline UTC, then workload ID. It chooses
  the earliest capacity-feasible start and uses input site order as its tie-break.
- **Capacity Only** uses the same workload order but chooses the placement with the largest minimum
  residual GPU capacity across all occupied hours. It then prefers earlier starts and input site
  order.
- **ThermalShift** creates CP-SAT binary variables for valid candidates. Phase 1 maximizes scheduled
  workload count. Phase 2 fixes that optimum and minimizes total modeled thermal exposure. Exposure
  coefficients are thermal stress-hours scaled by 1,000,000 and rounded to integers. Phase 3 fixes
  both prior optima and minimizes deterministic candidate rank.

CP-SAT uses one search worker and random seed 0. Workload priority remains in the domain model but
does not influence this MVP objective; no priority weights are invented.

Thermal stress-hours are modeled scheduling-decision units, not physical energy. Synthetic unit-test
comparisons demonstrate algorithm behavior only and are not FortyGuard hackathon benchmark evidence.
