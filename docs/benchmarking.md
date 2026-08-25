# Benchmarking ThermalShift

The benchmark runner applies an explicit same-input control: First Available,
Capacity Only, and ThermalShift receive the same immutable sites, workloads, and
one-hour `ThermalGrid`. They run in that fixed order. Runtime uses a monotonic,
high-resolution clock and is descriptive only; it never enters a scheduling
decision and can vary between runs.

Completion rate is scheduled workloads divided by all input workloads. Deadline
satisfaction rate is deadline-satisfied decisions divided by all input
workloads—not merely scheduled workloads—so dropping difficult jobs cannot
inflate the result. Total modeled thermal exposure is the sum of decision
exposure in **thermal stress-hours**, an interpreted scheduling metric rather
than a physical energy unit. Mean exposure per scheduled workload divides that
total by scheduled count. Mean occupied thermal stress divides it by scheduled
workload-hours. Peak occupied thermal stress is the maximum actual grid-slot
score occupied by a decision, recovered from the grid rather than from decision
averages.

## Fair comparisons and claims

A direct total-exposure percentage is valid only when candidate and baseline
schedule exactly the same workload-ID set. Equal sets matter because a policy
could otherwise appear cooler merely by omitting a costly workload. When sets
differ, the percentage is unavailable and output explains why. A zero-exposure
baseline also has no percentage. Negative percentages remain visible.

The headline helper makes a positive modeled-ambient-thermal claim only when
the workload sets match, ThermalShift preserves completion and deadline
satisfaction, and its reduction is positive. All other states receive a neutral
factual sentence.

## Evidence boundary

The included `offline-synthetic-v1` scenario is deterministic algorithm
demonstration data. Its values are synthetic thermal stress scores in `[0, 1]`,
not measured temperatures, and its percentages are not FortyGuard benchmark
evidence. Historical replay is implemented separately as a cache-only path and
is complete for both predeclared windows.

Ambient-derived modeled thermal stress cannot establish GPU temperature,
server inlet temperature, PUE, cooling energy, water consumption, electricity
use, or savings in any of those quantities. Such inferences require facility
telemetry that this project does not have.

## Evidence artifacts

The deterministic synthetic demonstration can write judge-readable JSON and
Markdown without network access:

```bash
python examples/run_synthetic_benchmark.py --output-dir runs/synthetic-demo
```

The output is explicitly classified as
`synthetic_demonstration` and is not FortyGuard benchmark evidence. It writes
`benchmark.json` and `report.md` beneath the selected directory.

For identical inputs, scenario definitions, scheduler decisions, modeled
thermal-exposure metrics, fairness comparisons, and site/workload ordering are
deterministic. JSON structure and key ordering are stable. `runtime_ms` is
measured execution metadata and may vary by machine or run; it is not rewritten
for artifact output. `generated_at_utc`, when supplied by a caller, is also
metadata rather than a scheduling input.

A complete cache-backed replay can write the same artifact pair:

```bash
python examples/run_historical_replay.py \
  --window summer-midday-v1 \
  --output-dir runs/summer-midday-v1
```

Historical output is classified as `fortyguard_historical_replay`: ambient
temperatures come from FortyGuard, while workloads and site GPU capacities are
modeled benchmark inputs. If calibration or replay cache inputs are incomplete,
the command exits nonzero and writes no artifacts. It never collects missing
data. FortyGuard confirmed on 2026-08-25 that Heatmap `date_time.start_time` is
AOI-local and that timezone and daylight-saving offset are inferred from polygon
coordinates; the ThermalShift adapter converts each orchestration UTC instant
accordingly.

## Completed historical evidence

Committed evidence lives under `evidence/`. Each `benchmark.json` is the exact,
machine-readable record; each `report.md` is its concise judge-facing rendering.

- `summer-midday-v1` is the primary historical comparison. All schedulers place
  the same 10 workloads with 100% deadline satisfaction. Total modeled exposure is
  16.592 stress-hours for First Available, 16.253 for Capacity Only, and 13.262 for
  ThermalShift. The fairness-valid reductions are 20.1% and 18.4%, respectively.
- `winter-overnight-v1` is robustness evidence near the lower model floor. The
  corresponding totals are 0.152, 0.168, and 0.000 stress-hours. ThermalShift's raw
  100% relative modeled reductions arise because its placements reach the 0.000
  floor against small positive baselines; they are not 100% cooling, energy,
  electricity, water, or facility savings.

Direct links:

- [Summer report](../evidence/summer-midday-v1/report.md) and
  [summer JSON](../evidence/summer-midday-v1/benchmark.json)
- [Winter report](../evidence/winter-overnight-v1/report.md) and
  [winter JSON](../evidence/winter-overnight-v1/benchmark.json)
