# Historical environmental data

FortyGuard remains ThermalShift's real environmental data source. The four locations are modeled
compute sites, and each request uses a small square area of interest centered on the site's public
coordinates. The initial adapter requests 100 m granularity over an approximately 400 m × 400 m
AOI. Those choices describe the request sent; they do not assert a finer output resolution.

The FortyGuard payload has date and time strings but no timezone field. ThermalShift converts each
requested timezone-aware instant into the modeled site's IANA timezone before serializing those
strings. FortyGuard interprets `date_time.start_time` as AOI-local time and automatically infers
timezone and daylight-saving offset from the AOI polygon coordinates. This behavior was confirmed
by the FortyGuard Hackathon Team on 2026-08-25. The original aware orchestration instant is retained
on the resulting domain observation.

For a completed heatmap, ThermalShift uses the AOI `temperature_stats.mean` as its raw
`TemperatureObservation`. Minimum and maximum remain descriptive result statistics; neither is the
primary observation.

Successful results are cached as validated JSON under `data/cache/fortyguard/`. Cache keys are
SHA-256 digests of the complete canonical request payload. Each record retains a schema version,
request payload, and validated result. This supports reproducibility and avoids duplicate successful
API work; credentials and request headers are never cached.

## Initial calibration sample

The dry-run collection plan combines four sites with seven deterministic UTC instants across 2024,
for 28 candidate requests. It deliberately varies season and time of day and was not selected using
known temperature outcomes. This is an initial calibration sample, not a statistically complete
climatic characterization.

Calibration diagnostics pool all observations across sites and use one common scale. P05/P95 and
P10/P90 are candidate pairs to inspect, not predetermined winning thresholds. Quantiles use linear
interpolation at the zero-based position `(n - 1) × q` in the sorted pooled sample.

Ambient observations and their modeled calibration diagnostics do not infer GPU temperature,
server inlet temperature, cooling energy, PUE, water use, or electricity savings.

Collectors emit only allow-listed structured failure diagnostics:
`terminal_activity_failed` means FortyGuard explicitly reported `Failed`;
`polling_timeout` means ThermalShift exhausted its bounded local wait;
`http_error` covers HTTP or transport failure; `response_error` means a response
could not be safely validated; and `generic_error` covers another locally handled
runtime or value failure. Activity IDs are retained after successful submission,
and numeric HTTP status is retained when available. Credentials, raw response
bodies, and arbitrary exception text remain suppressed.

Neither terminal failures nor timeouts are automatically retried. In particular,
a timed-out remote activity may still be running, so blind resubmission could
duplicate work. Following FortyGuard's recommendation for failed tasks, known
activity IDs are recorded for diagnosis or support.

By default, ThermalShift checks asynchronous status up to 120 times at five-second
intervals. The initial GET counts as the first check, sleeps occur only between
checks, and the client makes no more than 120 status GETs. This finite client-side
policy mirrors FortyGuard's public Quickstart as of this integration design; it is
not an API guarantee or a promise that every activity completes within that wait.
Status GETs are distinct from new `POST /v1/heatmap` submissions and do not consume
the collector's `--max-api-calls` submission budget. Exhausting the status-check
limit retains the activity ID, does not cache an incomplete result, and never
triggers an automatic replacement POST.

A `response_error` with an activity ID means submission succeeded, but the
subsequent status response could not be safely interpreted under the client
contract. It is not a terminal activity failure. Safe response reason codes and
validation field paths may be shown, but rejected values, raw bodies, and server
messages are not.

For diagnosis, `examples/check_fortyguard_activity.py` requires an existing
activity ID and the exact `CHECK_EXISTING_FORTYGUARD_ACTIVITY` confirmation. It
makes exactly one status GET, performs no polling or sleeping, never submits a
replacement task, and does not mutate the cache.

Its optional `--shape` mode safely summarizes type counts and lengths for the
normal-distribution axes plus finite allow-listed temperature aggregates. It
never exposes distribution members or `map_data`. This supports response-contract
diagnosis only; inspecting a malformed response shape does not make that response
valid under the existing schema.

One completed response was observed with equal temperature minimum, maximum,
and mean, zero standard deviation, a numeric normal-distribution x-axis, and an
all-null normal-distribution y-axis. ThermalShift accepts this observed
zero-variance representation only when the y-axis is non-empty and entirely
null, both normal-distribution axes have equal length, standard deviation is
zero, and minimum equals maximum equals mean. Arbitrary or mixed null
distributions remain invalid. Nulls are preserved and are never converted into
synthetic density values. `temperature_stats.mean` remains the historical
observation source and the normal-distribution y-axis is not a scheduling input.
This compatibility behavior reflects an observed response, not a universal
FortyGuard contract guarantee.

`examples/recover_calibration_activity.py` can associate an already completed
activity only with its exact entry in the frozen four-by-seven calibration plan.
With the exact `RECOVER_EXISTING_FORTYGUARD_CALIBRATION` confirmation, a cache
miss causes one status GET and no polling, retry, sleep, replacement POST, or
cache-key change. A cache hit makes no request. Only a matching, validated
`Completed` result is stored; raw response content, distributions, `map_data`,
and credentials are never printed.
