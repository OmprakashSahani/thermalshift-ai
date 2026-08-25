# ThermalShift AI — Submission Draft

> Near-final draft based on two complete, predeclared FortyGuard-backed
> historical replays. Demo and video URLs remain to be finalized.

## One-line pitch

Hyperlocal thermal-aware workload orchestration for distributed AI infrastructure.

## Project summary

Distributed AI operators can often choose where a flexible batch, training, or
evaluation workload runs and when it starts within a release-to-deadline window.
Conventional placement focuses on capacity and feasibility even when eligible
locations experience different ambient thermal conditions.

ThermalShift makes FortyGuard hyperlocal ambient-temperature observations an
operational scheduling input. It transforms historical AOI mean temperatures into
a normalized modeled thermal-stress score, builds a site-by-time thermal grid, and
evaluates three schedulers with identical inputs. First Available chooses the
earliest feasible placement; Capacity Only uses residual GPU capacity without
thermal optimization; and ThermalShift uses OR-Tools CP-SAT. Its lexicographic
objective first maximizes completed workloads, then minimizes total modeled ambient
thermal exposure, then applies deterministic tie-breaking. Eligible sites, modeled
GPU capacity, release time, duration, deadline, and thermal-grid availability remain
hard constraints.

Direct percentage comparisons are published only when candidate and baseline
schedule the same workload-ID set and preserve completion and deadline satisfaction.
On the predeclared summer replay using FortyGuard historical ambient temperatures,
ThermalShift scheduled the same 10/10 modeled workloads as both baselines with 100%
deadline satisfaction, while reducing modeled ambient thermal exposure by 20.1%
versus First Available and 18.4% versus Capacity Only. The corresponding totals were
16.592, 16.253, and 13.262 thermal stress-hours.

The contrasting predeclared winter replay provides robustness evidence near the
model floor: ThermalShift reached 0.000 stress-hours against small positive baseline
exposures of approximately 0.152 and 0.168. The raw relative reduction is 100%,
because the candidate reaches the modeled floor—not because real cooling, energy,
electricity, water, or facility savings are 100%.

Both historical replays use real FortyGuard ambient temperatures with four modeled
U.S. sites, modeled 64-GPU capacities, and ten modeled workloads. The pooled P10/P90
calibration and both replay windows were frozen before full hourly outcomes were
viewed. Missing inputs are never interpolated or replaced with synthetic data.
Thermal stress-hours are a modeled scheduling metric, not an energy unit, and do not
establish GPU temperature, server inlet temperature, PUE, cooling energy,
electricity consumption or savings, or water consumption or savings.

ThermalShift gives distributed AI infrastructure and platform teams an auditable
example of incorporating environmental intelligence into constraint-aware workload
placement without dropping work or overstating facility outcomes.

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
| Demo URL | TBD |
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
- [ ] Demo video recorded
- [ ] Public repository checked
- [ ] FortyGuard collaborator requirement checked
- [ ] Live-demo URL added if applicable
- [ ] Video URL added
- [ ] Final form submitted
- [x] Final summary <= 500 words
