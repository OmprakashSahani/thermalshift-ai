# Thermal stress model

ThermalShift uses a modeled thermal stress score so ambient-temperature observations can serve
as a transparent scheduling signal. The score is a relative decision metric; it does not describe
the thermal state or resource use of a facility.

For ambient temperature `T` and calibration parameters `lower_reference_c` and
`upper_reference_c`, where the upper reference is greater than the lower reference:

```text
raw_score = (T - lower_reference_c) / (upper_reference_c - lower_reference_c)
thermal_stress_score = clamp(raw_score, 0.0, 1.0)
```

Scores from 0.00 up to 0.25 are low risk, 0.25 up to 0.50 are moderate, 0.50 up to
0.75 are high, and 0.75 through 1.00 are extreme.

## Calibration

The two references are calibration parameters, not universal outdoor-temperature thresholds for
data centers. The planned benchmark methodology will derive common reference values from a pooled
FortyGuard historical temperature baseline spanning all candidate sites and the evaluation period,
using shared quantiles or reference values. No historical percentiles are assumed yet. Applying
common references makes site and scheduler comparisons use the same scale.

## Thermal exposure

For regularly sampled scores, modeled thermal exposure is:

```text
thermal exposure = sum(thermal_stress_score * interval_hours)
```

Its unit is **thermal stress-hours**. An empty series has zero exposure.

## Scientific limitations

This model transforms outdoor ambient temperature into an interpretable scheduling signal. It does
not directly measure GPU temperature, server inlet temperature, cooling energy, PUE, water use, or
electricity savings. Establishing any of those outcomes would require facility telemetry and a
separate validated physical model.
