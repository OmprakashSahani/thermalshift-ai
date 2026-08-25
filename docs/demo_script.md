# ThermalShift AI — Demo Script Draft

**Target:** 2:40–2:55 spoken, reliable offline execution, no live FortyGuard
request.

## 0:00–0:20 — Problem

**On screen:** README hero and “The operational problem.”

**Presenter says:**

“Distributed AI workloads often have flexibility in both location and start time,
but placement typically considers capacity and deadlines without ambient thermal
conditions. ThermalShift adds hyperlocal temperature as another decision signal
while preserving operational feasibility. It minimizes modeled ambient thermal
exposure—not measured cooling energy or facility efficiency.”

**Do not claim:** outdoor temperature directly measures GPU temperature, facility
efficiency, or energy use.

## 0:20–0:45 — FortyGuard and thermal stress

**On screen:** README “What ThermalShift does” and FortyGuard integration.

**Presenter says:**

“FortyGuard supplies the real historical ambient-temperature observations.
ThermalShift validates and caches each Heatmap result, then applies a frozen pooled
P10/P90 calibration to the AOI mean temperature. Exposure sums normalized modeled
stress across occupied hours. FortyGuard confirmed start time is AOI-local, so one
orchestration UTC instant becomes each site's local request time.”

**Do not claim:** P10/P90 are physical thresholds or stress-hours are energy units.

## 0:45–1:10 — Architecture and constraints

**On screen:** README Mermaid diagram and scheduler policies.

**Presenter says:**

“The thermal grid and modeled inputs meet at the scheduling layer. Placements must
satisfy eligibility, capacity, release time, duration, deadline, and grid
availability. We compare two baselines with ThermalShift's OR-Tools CP-SAT optimizer:
maximize completion, minimize modeled exposure at that completion count, then
tie-break deterministically. Direct percentages require identical workload sets.”

**Do not claim:** priority, carbon, pricing, or facility energy is optimized.

## 1:10–1:30 — Synthetic sanity check

**On screen:** Run:

```bash
python examples/run_synthetic_benchmark.py
```

**Presenter says:**

“The synthetic scenario is a quick offline sanity check. All schedulers place eight
workloads and meet every deadline; ThermalShift lowers the synthetic modeled score.
This demonstrates optimizer behavior only. It is not FortyGuard historical evidence
and is not the main result.”

**Do not claim:** synthetic percentages are historical or facility outcomes.

## 1:30–2:25 — FortyGuard historical evidence: main demo

**On screen:** Run the cache-only benchmark:

```bash
python examples/run_historical_replay.py \
  --window summer-midday-v1
```

Then open [`evidence/summer-midday-v1/report.md`](../evidence/summer-midday-v1/report.md).

**Presenter says:**

“Here is the primary FortyGuard-backed result. The predeclared summer window uses
real historical ambient temperatures across four modeled U.S. sites, with modeled
64-GPU capacities and ten modeled workloads. Every scheduler places the same ten of
ten workloads and preserves 100% deadline satisfaction. First Available records
16.592 thermal stress-hours, Capacity Only 16.253, and ThermalShift 13.262. Because
the sets match, direct comparison is valid: ThermalShift reduces modeled
ambient thermal exposure by 20.1% versus First Available and 18.4% versus Capacity
Only.”

**Optional on screen:** Open
[`evidence/winter-overnight-v1/report.md`](../evidence/winter-overnight-v1/report.md).

**Presenter says:**

“In the predeclared winter robustness window, ThermalShift reaches the modeled
stress floor at 0.000 stress-hours versus small positive baseline exposure. The
report explains that the resulting 100% relative modeled reduction is not 100%
real-world energy or cooling savings.”

**Do not show:** API keys, raw cache, cache keys, activity IDs, request payloads, or
raw `map_data`.

## 2:25–2:50 — Value, boundary, and close

**On screen:** README “Scientific boundaries” and “Why this is useful.”

**Presenter says:**

“ThermalShift incorporates hyperlocal environmental intelligence without sacrificing
capacity or deadlines. FortyGuard data drives decisions, and committed JSON and
Markdown make results auditable. Thermal stress-hours are a modeled scheduling
metric—not GPU temperature, PUE, cooling energy, electricity, water, or facility
savings. This is a practical foundation for thermal-aware orchestration, with room
for separately validated facility telemetry and operational signals in future
versions.”

**Do not claim:** production readiness, guaranteed savings, or measured facility
outcomes.

## Demo failure plan

If terminal execution fails during recording:

1. Open the committed
   [`evidence/summer-midday-v1/report.md`](../evidence/summer-midday-v1/report.md)
   first and narrate the verified primary result.
2. Use
   [`evidence/winter-overnight-v1/report.md`](../evidence/winter-overnight-v1/report.md)
   for the one-sentence robustness result.
3. Explain that both reports and their JSON records were produced by the repository's
   cache-only benchmark command.
4. Use pre-generated synthetic artifacts only as a secondary fallback.
5. Do not improvise unsupported claims or expose cache contents.

## Pre-recording checklist

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

## Recording readiness

- [ ] Terminal font and zoom are readable at video resolution
- [ ] Virtual environment and dependencies are ready
- [ ] Cache-only summer command has been rehearsed offline
- [ ] Committed historical reports are open as fallback tabs
- [ ] No API key, activity ID, cache key, raw response, or `map_data` is visible
- [ ] Final recording remains below three minutes
