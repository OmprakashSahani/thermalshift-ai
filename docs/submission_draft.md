# ThermalShift AI — Submission Draft

> Final submission copy based on two complete, predeclared FortyGuard-backed
> historical replays and the deployed interactive Scenario Lab. Video URL remains TBD.

## One-line pitch

Hyperlocal thermal-aware workload orchestration for distributed AI infrastructure.

## Project summary

Flexible AI workloads are normally scheduled primarily around capacity and deadlines,
even though local ambient thermal conditions vary by place and time. ThermalShift AI
uses FortyGuard hyperlocal historical ambient temperature as an operational signal for
deciding where and when flexible GPU workloads should run.

The implementation integrates the asynchronous FortyGuard Heatmap API with AOI-local
request-time handling, validated cache/replay inputs, and a frozen pooled P10/P90
calibration over 28 observations. Historical AOI mean temperatures become a
deterministic one-hour modeled thermal-stress grid shared across four modeled U.S.
sites with modeled 64-GPU capacities.

ThermalShift compares three actual scheduler implementations using identical inputs.
First Available chooses the earliest feasible placement. Capacity Only balances
residual modeled GPU capacity without using temperature for selection. ThermalShift
uses OR-Tools CP-SAT with a lexicographic objective: maximize completed workloads,
then minimize modeled ambient thermal exposure, then apply a deterministic tie-break.
Eligibility, capacity, release time, runtime, deadline, and grid availability remain
hard constraints.

The **official benchmark** is committed, predeclared historical evidence. In the
summer replay, ThermalShift reduced modeled ambient thermal exposure by **20.1% versus
First Available** and **18.4% versus Capacity Only** while all schedulers placed
**10/10 workloads** with **100% deadline satisfaction**. Direct percentages are
published only when scheduled workload-ID sets match. In the winter robustness
replay, ThermalShift reached the modeled stress floor against small positive baseline
exposures. That floor result must not be interpreted as 100% energy, cooling,
electricity, water, PUE, or facility savings.

The deployed **Scenario Lab** is explicitly an interactive simulation, not official
benchmark evidence. Judges can add one bounded modeled workload to the ten-workload
replay and rerun First Available, Capacity Only, and ThermalShift live against the
committed sanitized FortyGuard historical conditions. Interaction makes no
FortyGuard request and writes no evidence.

Thermal stress-hours are a modeled scheduling metric, not a physical energy unit.
ThermalShift does not establish GPU temperature, server inlet temperature, facility
efficiency, or resource savings; those claims require facility telemetry and separate
validated models.

## Track alignment

Primary alignment proposed by the project team:

- **Track 03 — Industrial & Enterprise:** ThermalShift addresses an operational
  infrastructure decision—placing flexible AI workloads across constrained sites
  and time windows.
- **Track 05 — Model Designing:** ThermalShift implements and evaluates an
  interpretable thermal-stress model and completion-first CP-SAT scheduler.

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
| Scenario Lab results | Interactive simulation; not official benchmark evidence |

## Current evidence status

### Calibration

- Complete frozen set: **28/28 observations**
- Frozen rule: **pooled P10/P90**
- Lower reference: **4.567570294117648 °C**
- Upper reference: **37.01878625 °C**

These are shared model calibration references, not universal physical thresholds.

### Synthetic benchmark

- Complete and publishable as a synthetic optimizer demonstration
- 8/8 workloads and 100% deadline satisfaction across all schedulers
- ThermalShift: 2.560 stress-hours; 75.1% below First Available and 72.2% below
  Capacity Only

### Historical replay

- Summer replay: **complete and reviewed**
- Winter replay: **complete and reviewed**
- Evidence artifacts: **committed** under `evidence/`
- Same-workload fairness gate: valid for both baseline comparisons in both windows

### Interactive Scenario Lab

- Deployed and manually verified on Render
- Adds one bounded modeled workload to the existing ten-workload replay
- Reruns the actual First Available, Capacity Only, and ThermalShift implementations
- Uses committed sanitized FortyGuard historical conditions with zero interaction-time
  FortyGuard requests
- Explicitly classified as simulation, not official benchmark evidence

FortyGuard confirmed that Heatmap `date_time.start_time` is AOI-local and that
timezone and daylight-saving offset are inferred from the AOI polygon. ThermalShift
converts each orchestration UTC instant into each modeled site's local time before
serialization. Confirmed by the FortyGuard Hackathon Team on 2026-08-25.

## Submission fields

| Field | Draft value |
|---|---|
| Project name | ThermalShift AI |
| Tagline | Hyperlocal thermal-aware workload orchestration for distributed AI infrastructure. |
| Primary tracks | Track 03 — Industrial & Enterprise; Track 05 — Model Designing |
| Repository | https://github.com/OmprakashSahani/thermalshift-ai |
| Team | Solo participant |
| Technology | Python 3.12, FortyGuard Temperature API, OR-Tools CP-SAT, HTTPX, Pydantic, pytest, Ruff |
| Demo URL | https://thermalshift-ai.onrender.com/ |
| Video URL | TBD |

## Scientific boundary

ThermalShift models ambient thermal stress and thermal stress-hours for scheduling.
It does not establish GPU temperature, server inlet temperature, PUE, cooling
energy, electricity consumption or savings, water consumption or savings, or
facility savings. Those outcomes require facility telemetry and separate validated
models.

## Submission finalization checklist

- [x] FortyGuard timezone response received
- [x] Adapter semantics confirmed
- [x] Summer replay complete
- [x] Summer historical artifact generated
- [x] Summer historical comparison reviewed
- [x] Winter replay complete
- [x] Winter historical artifact generated
- [x] Winter historical comparison reviewed
- [x] README historical evidence updated
- [x] Submission summary updated with validated historical result
- [x] Demo script updated
- [x] Live demo deployed
- [x] Live demo URL added
- [x] Live Scenario Lab manually verified
- [ ] Demo video recorded
- [ ] Public repository checked
- [ ] FortyGuard collaborator requirement checked
- [ ] Video URL added
- [ ] Final form submitted
- [x] Final summary <= 500 words
