# Historical environmental data

FortyGuard remains ThermalShift's real environmental data source. The four locations are modeled
compute sites, and each request uses a small square area of interest centered on the site's public
coordinates. The initial adapter requests 100 m granularity over an approximately 400 m × 400 m
AOI. Those choices describe the request sent; they do not assert a finer output resolution.

The FortyGuard payload has date and time strings but no timezone field. ThermalShift converts each
requested timezone-aware instant into the modeled site's IANA timezone before serializing those
strings. The original aware instant is retained on the resulting domain observation. This adapter
behavior does not prove undocumented FortyGuard timezone semantics and must be rechecked against
hackathon or API guidance if FortyGuard clarifies request-time interpretation.

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

Terminal `Failed` activities are not retried automatically. Following FortyGuard's
recommendation to record activity IDs for failed tasks, collectors print the safe
activity ID for diagnosis or support while suppressing credentials, raw response
bodies, and arbitrary exception text.
