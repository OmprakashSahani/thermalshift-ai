# ThermalShift AI — Three-Minute Demo Script

**Primary demo:** https://thermalshift-ai.onrender.com/

**Target finished-video runtime:** approximately 2:35–2:45 with normal UI interaction
and brief pauses, leaving margin below the three-minute limit. The deployed dashboard is the primary visual;
no live FortyGuard request is required.

## 0:00–0:18 — Problem and solution

**On screen:** Open the deployed dashboard at the official Summer midday evidence.

**Presenter says:**

“Flexible AI workloads can move across locations or time, but scheduling usually
focuses on capacity and deadlines. ThermalShift uses FortyGuard historical ambient
temperature to choose feasible placements with lower modeled ambient thermal
exposure.”

## 0:18–0:50 — Official summer evidence

**On screen:** Point to the hero metrics and scheduler comparison.

**Presenter says:**

“This is committed official historical benchmark evidence. In the predeclared summer
replay, ThermalShift reduced modeled ambient thermal exposure by 20.1 percent versus
First Available and 18.4 percent versus Capacity Only. Every scheduler placed all ten
workloads with 100 percent deadline satisfaction. FortyGuard historical ambient
temperature is real input. The sites, 64-GPU capacities, workloads, and stress metric
are modeled—not facility telemetry.”

## 0:50–1:10 — Completion-first scheduling

**On screen:** Compare the three official scheduler rows.

**Presenter says:**

“The baselines select by availability or remaining capacity. ThermalShift uses
OR-Tools CP-SAT to preserve maximum workload completion first, then minimize modeled
thermal exposure. Modeled capacity, eligible sites, release time, runtime, and
deadlines remain hard constraints.”

## 1:10–2:05 — Run Scenario Lab

**On screen:** Scroll to Scenario Lab. Keep the default summer settings: 16 GPUs,
two hours, release at 18:00 UTC, deadline at 22:00 UTC, all four modeled sites.
Click **Run ThermalShift**.

**Presenter says:**

“Now I’ll add one modeled workload: 16 GPUs for two hours, available from 18:00 to
22:00 UTC, with all four modeled sites eligible. This is an interactive simulation,
not official benchmark evidence. Run ThermalShift calls the backend, adds this work
to the ten-workload replay, and reruns the existing scheduler implementations against
committed FortyGuard historical conditions.

First Available chooses Ashburn from 18:00 to 20:00. Capacity Only chooses Atlanta
from 18:00 to 20:00. ThermalShift shifts the workload to Atlanta from 20:00 to 22:00.
All three still place 11 of 11 workloads and meet every deadline.

This site-by-time landscape shows the FortyGuard historical ambient temperature and
modeled stress behind those different choices.”

## 2:05–2:22 — Fairness rule

**On screen:** Point to the Scenario Lab fairness message, without running the edge
case.

**Presenter says:**

“Direct percentages appear only when schedulers complete the same workload-ID set.
If one drops the custom workload, the percentage becomes unavailable instead of
making omitted work look like an improvement.”

## 2:22–2:40 — Boundary and close

**On screen:** Point to the REAL, MODELED, LIVE, and NOT MEASURED labels.

**Presenter says:**

“ThermalShift turns FortyGuard environmental intelligence into an operational signal
for flexible distributed AI workloads. Thermal stress-hours are a modeled scheduling
metric—not measured cooling, energy, water, PUE, or facility savings. The result is
a clear, reproducible, auditable workload decision that keeps feasibility first.”

## Recording guardrails

- Do not describe Scenario Lab as official benchmark evidence.
- Do not imply the application uses live or real-time FortyGuard conditions.
- Do not call stress-hours an energy unit or claim facility savings.
- Do not show credentials, private cache data, activity IDs, request payloads, or
  `map_data`.
- Do not run a collector or make a FortyGuard request during recording.

## Offline committed-evidence fallback

If hosting is unavailable during recording:

1. Open the committed
   [summer report](../evidence/summer-midday-v1/report.md) and narrate the verified
   20.1%, 18.4%, 10/10, and 100% result.
2. Use the [summer benchmark JSON](../evidence/summer-midday-v1/benchmark.json) if a
   machine-readable record is useful on screen.
3. Mention the [winter report](../evidence/winter-overnight-v1/report.md) only as
   robustness evidence near the modeled stress floor.
4. Explain that the committed reports were produced by the cache-only benchmark
   path. Do not substitute synthetic results for official evidence.

## Pre-recording checklist

- [x] Summer and winter historical evidence reviewed
- [x] Live demo deployed
- [x] Live Scenario Lab manually verified
- [x] Live demo URL added
- [ ] Demo video recorded
- [ ] Public repository checked
- [ ] FortyGuard collaborator requirement checked
- [ ] Video URL added
- [ ] Final form submitted
- [ ] Browser zoom and text are readable at recording resolution
- [ ] Committed reports are open as fallback tabs
- [ ] Final recording remains below three minutes
