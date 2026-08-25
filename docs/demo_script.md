# ThermalShift AI — Demo Script Draft

**Target spoken duration:** approximately 2:43 at 135 words per minute.

**Demo mode:** reliable offline execution; no live FortyGuard API request.

## 0:00–0:20 — Problem

**On screen:** Open the GitHub README at the hero and “The operational problem.”

**Presenter says:**

“Distributed AI workloads often have flexibility in both location and start time,
but placement usually considers capacity and deadlines without considering ambient
thermal conditions. ThermalShift adds hyperlocal temperature as another decision
signal while keeping operational feasibility first. It optimizes modeled ambient
thermal exposure—not measured cooling energy.”

**Do not claim:** that outdoor temperature directly measures GPU temperature,
facility efficiency, or energy use.

## 0:20–0:45 — FortyGuard and the concept

**On screen:** Scroll to “What ThermalShift does” and the FortyGuard integration
section.

**Presenter says:**

“FortyGuard is the environmental data source. ThermalShift submits a Heatmap
request, polls the asynchronous activity with a finite policy, validates the
result, and caches successful observations. The AOI mean ambient temperature feeds
a pooled calibration, producing a normalized thermal-stress score from zero to
one. Workload exposure is the sum of occupied hourly scores, reported as modeled
thermal stress-hours.”

**Do not claim:** that thermal stress-hours are an energy unit or that missing data
is replaced.

## 0:45–1:15 — Architecture and constraints

**On screen:** Show the README Mermaid architecture, then the scheduler-policy
section.

**Presenter says:**

“Modeled sites and workloads join the temperature-derived thermal grid at the
scheduling layer. Every placement must satisfy site eligibility, GPU capacity,
release time, duration, deadline, and grid availability. We compare two
temperature-unaware baselines—First Available and Capacity Only—with ThermalShift’s
OR-Tools CP-SAT optimizer. Its objective is lexicographic: maximize completed work,
then minimize modeled thermal exposure, then apply deterministic tie-breaking.”

**Do not claim:** that priority, carbon, pricing, or facility energy is part of the
current objective.

## 1:15–1:55 — Synthetic demonstration

**On screen:** Run:

```bash
python examples/run_synthetic_benchmark.py
```

Then generate and open the report:

```bash
python examples/run_synthetic_benchmark.py \
  --output-dir runs/synthetic-demo
```

Open `runs/synthetic-demo/report.md` at the scheduler table.

**Presenter says:**

“All three schedulers place the same eight workloads and preserve every deadline.
First Available produces 10.300 thermal stress-hours, Capacity Only 9.220, and
ThermalShift 2.560. Because the scheduled workload set is identical, the fairness
gate allows direct comparison: ThermalShift is 75.1% lower than First Available
and 72.2% lower than Capacity Only. These are synthetic thermal-score results that
demonstrate optimizer behavior—not claims of real energy, cooling, water, or PUE
savings. The same run can produce auditable JSON and Markdown artifacts.”

**Do not claim:** that these percentages are FortyGuard historical results or
facility savings. Do not compare scheduler runtime as a performance result.

## 1:55–2:25 — Historical replay design

**On screen:** Show the README historical replay section or
`docs/historical_replay.md`. If useful, run the cache-only command:

```bash
python examples/run_historical_replay.py \
  --window summer-midday-v1
```

**Presenter says:**

“The historical path uses FortyGuard ambient temperatures across four modeled U.S.
sites, a frozen pooled P10/P90 calibration, two predeclared replay windows, and ten
modeled workloads under identical scheduler constraints. Execution is cache-only.
If any required observation is missing, ThermalShift exits without a benchmark;
there is no synthetic fallback. FortyGuard confirmed that Heatmap start time is
AOI-local and that timezone and DST are inferred from the polygon, so ThermalShift
converts one orchestration UTC instant into each site's local request time.
Historical evidence remains pending until the selected replay data is complete.”

**Do not claim:** a historical reduction percentage before the selected replay is
complete and reviewed.

## 2:25–2:45 — Impact and close

**On screen:** Return to the README “Scientific boundaries” and “Why this is
useful” sections.

**Presenter says:**

“ThermalShift shows how infrastructure teams can add hyperlocal environmental
intelligence to workload placement without sacrificing capacity or deadline
constraints. FortyGuard data is a scheduling input, not a decorative dashboard.
The evidence layer separates synthetic demonstrations from historical replay, and
the fairness gate prevents lower exposure claims created by dropping work. The
result is a practical, auditable foundation for thermal-aware AI orchestration.”

**Do not claim:** production readiness, guaranteed savings, or measured facility
outcomes.

## Demo failure plan

If terminal execution fails during recording:

1. Open the already generated `runs/synthetic-demo/report.md` and
   `runs/synthetic-demo/benchmark.json`.
2. Explain that both were produced by the same offline repository command shown in
   the script.
3. Narrate only the verified synthetic metrics above; do not improvise unsupported
   claims.

If historical replay remains incomplete, show the cache-only command refusing to
run and explain that this is intentional evidence-integrity behavior. The refusal
demonstrates that ThermalShift does not fabricate missing data; it is not a demo
failure.

## Pre-recording checklist

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

## Recording readiness

- [ ] Terminal font and zoom are readable at video resolution
- [ ] Virtual environment and dependencies are ready
- [ ] Synthetic command has been rehearsed offline
- [ ] Synthetic artifacts are pre-generated as fallback
- [ ] No API key, activity ID, cache key, raw response, or `map_data` is visible
- [ ] Final recording remains below three minutes
