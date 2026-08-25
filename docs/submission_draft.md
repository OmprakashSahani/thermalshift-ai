# ThermalShift AI — Submission Draft

> Draft status: historical replay evidence is not finalized. FortyGuard Heatmap
> `start_time` timezone semantics are confirmed; selected replay collection remains
> incomplete.

## One-line pitch

Hyperlocal thermal-aware workload orchestration for distributed AI infrastructure.

## Project summary

Distributed AI operators can often choose where a flexible batch, training, or
evaluation workload runs and when it starts within a release-to-deadline window.
Traditional placement policies focus on capacity and feasibility while ignoring
that eligible locations may experience different ambient thermal conditions.

ThermalShift adds FortyGuard hyperlocal ambient-temperature data as an operational
scheduling signal. It converts historical observations into a normalized modeled
thermal-stress score, builds a site-by-time thermal grid, and evaluates three
schedulers against identical workloads and modeled capacities. First Available
chooses the earliest feasible placement. Capacity Only balances residual GPU
capacity without optimizing thermal stress. ThermalShift uses OR-Tools CP-SAT with
a lexicographic objective: first maximize completed workloads, then minimize total
modeled ambient thermal exposure, then apply deterministic tie-breaking. Eligible
sites, GPU capacity, release time, duration, deadline, and thermal-grid availability
remain hard constraints.

The benchmark reports thermal exposure in thermal stress-hours and permits direct
percentage comparisons only when candidate and baseline schedule the same workload
set. In the **synthetic demonstration—not FortyGuard historical evidence**,
ThermalShift schedules 8/8 workloads, preserves 100% deadline satisfaction, and
records 2.560 thermal stress-hours: 75.1% below First Available and 72.2% below
Capacity Only. These results demonstrate optimizer behavior on synthetic thermal
scores; they do not establish electricity, cooling, water, PUE, or monetary savings.

The historical replay path uses cached FortyGuard ambient temperatures, a frozen
pooled P10/P90 calibration, four modeled U.S. sites, ten modeled workloads, modeled
64-GPU capacities, and predeclared replay windows. It runs all schedulers under the
same constraints and refuses to benchmark incomplete data—there is no synthetic
fallback or interpolation. Historical replay evidence remains pending while the
selected replay data is completed.

ThermalShift is relevant to distributed AI infrastructure operators, batch and
training platform teams, and infrastructure researchers exploring how external
environmental intelligence can augment workload placement without displacing
operational constraints or overstating facility outcomes.

## Track alignment

Primary alignment proposed by the project team:

- **Track 03 — Industrial & Enterprise:** ThermalShift addresses an operational
  infrastructure decision—placing flexible AI workloads across constrained sites
  and time windows.
- **Track 05 — Model Designing:** ThermalShift implements and evaluates an
  interpretable thermal-stress model and a completion-first CP-SAT scheduling model.

## What is real vs modeled

| Component | Classification |
|---|---|
| FortyGuard historical ambient temperatures | Real external environmental data |
| Modeled sites | Benchmark constructs, not identified real facilities |
| 64-GPU site capacities | Modeled benchmark parameters |
| Workloads | Modeled benchmark inputs, not customer workloads |
| Thermal stress | Modeled normalized decision signal in `[0, 1]` |
| Thermal stress-hours | Modeled scheduling metric, not an energy unit |
| Scheduler decisions | Computed by the repository implementation |

## Current evidence status

### Calibration

- Complete frozen calibration set: **28/28 observations**
- Frozen rule: **pooled P10/P90**
- Lower reference: **4.567570294117648 °C**
- Upper reference: **37.01878625 °C**

These are shared model calibration references, not universal physical safety
thresholds.

### Synthetic benchmark

- Complete and publishable as a **synthetic demonstration**
- ThermalShift schedules **8/8** workloads
- Deadline satisfaction: **100%**
- Total modeled thermal exposure: **2.560 thermal stress-hours**
- Reduction versus First Available: **75.1%**
- Reduction versus Capacity Only: **72.2%**

### Historical replay

- Framework: complete
- Evidence: not finalized
- Selected replay data collection: incomplete
- Historical reduction percentages: **do not insert yet**

FortyGuard confirmed that Heatmap `date_time.start_time` is AOI-local and that
timezone and daylight-saving offset are inferred from the AOI polygon. ThermalShift
therefore converts each requested orchestration UTC instant into each modeled
site's local time before serialization. Confirmed by the FortyGuard Hackathon Team
on 2026-08-25.

## Submission fields

| Field | Draft value |
|---|---|
| Project name | ThermalShift AI |
| Tagline | Hyperlocal thermal-aware workload orchestration for distributed AI infrastructure. |
| Primary tracks | Track 03 — Industrial & Enterprise; Track 05 — Model Designing |
| Repository | https://github.com/OmprakashSahani/thermalshift-ai |
| Team | Solo participant |
| Technology | Python 3.12, FortyGuard Temperature API, OR-Tools CP-SAT, HTTPX, Pydantic, pytest, Ruff |
| Demo URL | TBD |
| Video URL | TBD |

## Scientific boundary

ThermalShift models ambient thermal stress and thermal stress-hours for scheduling.
It does not establish GPU temperature, server inlet temperature, PUE, cooling
energy, electricity consumption or savings, water consumption or savings, or
monetary savings. Those outcomes require facility telemetry and separate validated
models.

## Submission finalization checklist

- [x] FortyGuard timezone response received
- [x] Adapter semantics confirmed
- [ ] Summer replay complete
- [ ] Historical artifact generated
- [ ] Historical comparison reviewed
- [ ] README historical evidence updated
- [ ] Submission summary updated with historical result only if valid
- [ ] Demo script updated
- [ ] Demo video recorded
- [ ] Public repository checked
- [ ] FortyGuard collaborator requirement checked
- [ ] Live-demo URL added if applicable
- [ ] Video URL added
- [ ] Final summary <= 500 words
