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

## Predeclared windows

- `summer-midday-v1`: 2024-07-15 18:00Z through 23:00Z.
- `winter-overnight-v1`: 2024-01-15 06:00Z through 11:00Z.

Each window was defined as a six-hour, one-hour-resolution extension of an
instant already present in the calibration plan. Both definitions and the ten
modeled workloads are fixed before newly collected hourly outcomes are viewed.
Summer results must not influence workload definitions. The winter window was
predeclared as a contrasting validation window before summer replay results.
No temperature outcome is presumed for either window.

FortyGuard supplies real historical ambient temperatures. The ten workloads
and each modeled site's 64-GPU capacity are benchmark parameters, not customer
workloads or real facility telemetry. Cached AOI mean temperature is assessed
through the calibrated model; scheduling uses the resulting `[0, 1]` thermal
stress score rather than Celsius.

## Request-time boundary

`requested_utc` is ThermalShift orchestration metadata. The current payload
adapter converts that instant to the site's IANA local time because the
FortyGuard request contains date/time strings without a timezone field. This
is an explicit adapter assumption. Current public Heatmap documentation does
not prove the input timezone interpretation, so exact synchronized cross-site
absolute-time semantics must not be claimed until FortyGuard documentation or
support confirms them.

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

When FortyGuard reports a terminal `Failed` activity, it is not retried
automatically. Consistent with FortyGuard documentation recommending that
activity IDs be recorded for failed tasks, the collector prints that safe ID
for diagnosis or support while credentials, raw responses, and arbitrary
exception details remain suppressed.

The collector never starts a benchmark automatically. Original 4-by-7
calibration collection remains the responsibility of the separate calibration
collector; replay collection only displays its readiness. Replay windows,
plans, and modeled workloads must not be changed in response to observed
temperature results.
