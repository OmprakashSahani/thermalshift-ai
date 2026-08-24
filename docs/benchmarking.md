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
evidence. This benchmark layer does not implement real historical replay or
collect FortyGuard data. Real benchmark percentages must come only from a later
reproducible FortyGuard-backed replay.

Ambient-derived modeled thermal stress cannot establish GPU temperature,
server inlet temperature, PUE, cooling energy, water consumption, electricity
use, or savings in any of those quantities. Such inferences require facility
telemetry that this project does not have.
