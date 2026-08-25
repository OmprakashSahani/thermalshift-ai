# Offline historical replay

Historical replay separates two real FortyGuard ambient-temperature datasets.
The original calibration sample contains 28 observations: four modeled sites
at seven seasonally and diurnally varied instants. A replay window contains 24
different observations: four sites at six consecutive one-hour slots. Missing
cache records are never interpolated, replaced with calibration values, or
filled with synthetic data.

The frozen calibration rule is pooled **P10/P90**: P10 is the lower reference
and P90 is the upper reference for the existing `ThermalStressModel`. The rule,
not any currently observed numeric value, is fixed. Pooling establishes one
common interpretable scale across all modeled sites and is less sensitive to
individual extreme-tail observations than min/max or a more tail-heavy rule.
It is a modeling calibration rule, not a universal physical threshold and is
not claimed to be optimal. Official replay requires all 28 observations;
partial diagnostics are explicitly provisional.

The complete frozen 28/28 set produces a lower reference of
4.567570294117648 °C and an upper reference of 37.01878625 °C.

## Predeclared windows

- `summer-midday-v1`: 2024-07-15 18:00Z through 23:00Z.
- `winter-overnight-v1`: 2024-01-15 06:00Z through 11:00Z.

Each window was defined as a six-hour, one-hour-resolution extension of an
instant already present in the calibration plan. Both definitions and the ten
modeled workloads are fixed before newly collected hourly outcomes are viewed.
Summer results must not influence workload definitions. The winter window was
predeclared as a contrasting validation window before summer replay results.
No temperature outcome was presumed for either window when it was selected.

## Completed replay evidence

Both predeclared windows are now complete. This completion does not change their
predeclaration history: the window definitions and modeled workloads were fixed
before their full hourly outcomes were viewed.

| Window | First Available | Capacity Only | ThermalShift | Fairness-valid result |
|---|---:|---:|---:|---|
| `summer-midday-v1` | 16.592 stress-hours | 16.253 stress-hours | 13.262 stress-hours | 20.1% lower vs First Available; 18.4% lower vs Capacity Only |
| `winter-overnight-v1` | 0.152 stress-hours | 0.168 stress-hours | 0.000 stress-hours | Candidate reaches the modeled thermal-stress floor |

All three schedulers place 10/10 workloads and preserve 100% deadline satisfaction
in both windows. They schedule the same workload-ID set, so the direct-comparison
fairness gate is valid.

The summer replay is the primary historical result: ThermalShift reduces modeled
ambient thermal exposure by 20.1% versus First Available and 18.4% versus Capacity
Only. Winter is contrasting robustness evidence near the lower model floor. Its raw
100% relative reductions mean ThermalShift reaches 0.000 modeled stress-hours
against small positive baseline values; they do not mean 100% cooling, energy,
electricity, water, or facility savings.

Committed artifacts:

- [Summer judge-facing report](../evidence/summer-midday-v1/report.md) and
  [machine-readable JSON](../evidence/summer-midday-v1/benchmark.json)
- [Winter judge-facing report](../evidence/winter-overnight-v1/report.md) and
  [machine-readable JSON](../evidence/winter-overnight-v1/benchmark.json)

FortyGuard supplies real historical ambient temperatures. The ten workloads
and each modeled site's 64-GPU capacity are benchmark parameters, not customer
workloads or real facility telemetry. Cached AOI mean temperature is assessed
through the calibrated model; scheduling uses the resulting `[0, 1]` thermal
stress score rather than Celsius.

## Request-time semantics

`requested_utc` is ThermalShift orchestration metadata. The payload adapter
converts that instant to each site's IANA local time before serializing
`date_time.start_time`. FortyGuard interprets that value as AOI-local time and
infers the timezone and daylight-saving offset from the AOI polygon coordinates.
This behavior was confirmed by the FortyGuard Hackathon Team on 2026-08-25 and
supports representing one orchestration UTC instant with the corresponding local
wall-clock time for each modeled site.

Replay inherits the benchmark layer's same-input controls and fairness rule:
direct total-exposure percentages require identical scheduled workload sets.
Ambient-temperature-derived stress does not establish GPU or server-inlet
temperature, PUE, cooling energy, electricity use or savings, or water use.

## Collection safety

Replay collection is dry-run by default. Real collection requires `--submit`,
the exact `COLLECT_FORTYGUARD_REPLAY` confirmation, and a positive bounded
`--max-api-calls` value supplied explicitly. The conservative limit shown by
default is 4. Cache hits never consume that new-call budget. Processing is
sequential in the predeclared hour-major plan order, and
each successful response is persisted immediately by the cache-first
historical service. One failure stops all later new submissions without
discarding earlier successes; exception details and credentials are not
printed.

The default asynchronous wait makes at most 120 status GETs at five-second
intervals, matching FortyGuard's public Quickstart as of the integration design.
This is a finite client policy, not a guarantee that every activity will finish in
that period. The initial GET is one check and there is no sleep after the final
check. These polling GETs do not count against `--max-api-calls`, which limits only
new heatmap POST submissions. A timeout is not cached or automatically replaced
with another POST; its activity ID is retained and later new submissions stop.

Failure output distinguishes `terminal_activity_failed`, `polling_timeout`,
`http_error`, `response_error`, and `generic_error`. A terminal failure means
FortyGuard explicitly reported `Failed`; a polling timeout means only that
ThermalShift exhausted its bounded local wait. The remote activity may still
continue after a timeout, so it is not blindly resubmitted because doing so
could create duplicate work. Known activity IDs and numeric HTTP statuses are
retained for diagnosis or support, consistent with FortyGuard guidance to
record failed-task activity IDs. Credentials, raw responses, and arbitrary
exception details remain suppressed.

The collector never starts a benchmark automatically. Original 4-by-7
calibration collection remains the responsibility of the separate calibration
collector; replay collection only displays its readiness. Replay windows,
plans, and modeled workloads must not be changed in response to observed
temperature results.
