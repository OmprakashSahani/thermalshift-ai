# ThermalShift Benchmark Report

## Evidence classification

FORTYGUARD-BACKED HISTORICAL REPLAY

REAL HISTORICAL AMBIENT TEMPERATURES + MODELED WORKLOADS

## Scenario

- Scenario ID: `fortyguard-summer-midday-v1`
- Description: FortyGuard supplies real historical ambient-temperature observations; workload and 64-GPU capacity inputs are modeled benchmark parameters, not real facility telemetry.
- Data source: `FORTYGUARD_HISTORICAL_TEMPERATURES_WITH_MODELED_WORKLOADS`
- Generated at UTC: not supplied

## Calibration / provenance

- Replay window: `summer-midday-v1` starting 2024-07-15T18:00:00Z
- Replay slots: 6
- Calibration: 28 observations; `pooled_p10_p90`
- Calibration references: 4.567570294117648°C / 37.01878625°C
- Request-time interpretation: AOI-local start_time; FortyGuard infers timezone and DST from AOI polygon coordinates; ThermalShift converts each orchestration UTC instant to the modeled site local time before submission

## Scheduler results

| Scheduler | Scheduled | Unscheduled | Completion | Deadline satisfaction | Stress-hours | Mean occupied stress | Peak occupied stress | Runtime ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| first_available | 10 | 0 | 100.0% | 100.0% | 16.592 | 0.976 | 1.000 | 1.619 |
| capacity_only | 10 | 0 | 100.0% | 100.0% | 16.253 | 0.956 | 1.000 | 2.587 |
| thermalshift | 10 | 0 | 100.0% | 100.0% | 13.262 | 0.780 | 0.976 | 23.907 |

## ThermalShift comparisons

- **ThermalShift vs First Available:** ThermalShift reduced modeled ambient thermal exposure by 20.1% versus First Available while preserving 100.0% deadline satisfaction.
- **ThermalShift vs Capacity Only:** ThermalShift reduced modeled ambient thermal exposure by 18.4% versus Capacity Only while preserving 100.0% deadline satisfaction.

## Scheduling decisions

### first_available

| Workload | Site | Start | End | Exposure | Mean stress | Deadline | Capacity | Reason |
|---|---|---|---|---:|---:|:---:|:---:|---|
| w01 | ashburn-va | 2024-07-15T18:00:00Z | 2024-07-15T20:00:00Z | 1.9865452653424884 | 0.9932726326712442 | True | True | Earliest feasible placement using stable site order; temperature not used for selection. |
| w02 | ashburn-va | 2024-07-15T18:00:00Z | 2024-07-15T20:00:00Z | 1.9865452653424884 | 0.9932726326712442 | True | True | Earliest feasible placement using stable site order; temperature not used for selection. |
| w03 | ashburn-va | 2024-07-15T18:00:00Z | 2024-07-15T21:00:00Z | 2.961205536898478 | 0.9870685122994928 | True | True | Earliest feasible placement using stable site order; temperature not used for selection. |
| w04 | ashburn-va | 2024-07-15T19:00:00Z | 2024-07-15T20:00:00Z | 0.9941215993182091 | 0.9941215993182091 | True | True | Earliest feasible placement using stable site order; temperature not used for selection. |
| w05 | phoenix-az | 2024-07-15T19:00:00Z | 2024-07-15T21:00:00Z | 2.0 | 1.0 | True | True | Earliest feasible placement using stable site order; temperature not used for selection. |
| w06 | san-antonio-tx | 2024-07-15T20:00:00Z | 2024-07-15T21:00:00Z | 1.0 | 1.0 | True | True | Earliest feasible placement using stable site order; temperature not used for selection. |
| w07 | ashburn-va | 2024-07-15T20:00:00Z | 2024-07-15T22:00:00Z | 1.8228470465385471 | 0.9114235232692736 | True | True | Earliest feasible placement using stable site order; temperature not used for selection. |
| w08 | ashburn-va | 2024-07-15T18:00:00Z | 2024-07-15T19:00:00Z | 0.9924236660242794 | 0.9924236660242794 | True | True | Earliest feasible placement using stable site order; temperature not used for selection. |
| w09 | phoenix-az | 2024-07-15T18:00:00Z | 2024-07-15T20:00:00Z | 2.0 | 1.0 | True | True | Earliest feasible placement using stable site order; temperature not used for selection. |
| w10 | ashburn-va | 2024-07-15T21:00:00Z | 2024-07-15T22:00:00Z | 0.8481867749825573 | 0.8481867749825573 | True | True | Earliest feasible placement using stable site order; temperature not used for selection. |

### capacity_only

| Workload | Site | Start | End | Exposure | Mean stress | Deadline | Capacity | Reason |
|---|---|---|---|---:|---:|:---:|:---:|---|
| w01 | phoenix-az | 2024-07-15T18:00:00Z | 2024-07-15T20:00:00Z | 2.0 | 1.0 | True | True | Largest minimum residual GPU capacity; temperature not used for selection. |
| w02 | san-antonio-tx | 2024-07-15T18:00:00Z | 2024-07-15T20:00:00Z | 1.9381480033682328 | 0.9690740016841164 | True | True | Largest minimum residual GPU capacity; temperature not used for selection. |
| w03 | atlanta-ga | 2024-07-15T18:00:00Z | 2024-07-15T21:00:00Z | 2.8572485309549616 | 0.9524161769849872 | True | True | Largest minimum residual GPU capacity; temperature not used for selection. |
| w04 | ashburn-va | 2024-07-15T19:00:00Z | 2024-07-15T20:00:00Z | 0.9941215993182091 | 0.9941215993182091 | True | True | Largest minimum residual GPU capacity; temperature not used for selection. |
| w05 | ashburn-va | 2024-07-15T20:00:00Z | 2024-07-15T22:00:00Z | 1.8228470465385471 | 0.9114235232692736 | True | True | Largest minimum residual GPU capacity; temperature not used for selection. |
| w06 | san-antonio-tx | 2024-07-15T20:00:00Z | 2024-07-15T21:00:00Z | 1.0 | 1.0 | True | True | Largest minimum residual GPU capacity; temperature not used for selection. |
| w07 | san-antonio-tx | 2024-07-15T21:00:00Z | 2024-07-15T23:00:00Z | 1.9887312003809918 | 0.9943656001904959 | True | True | Largest minimum residual GPU capacity; temperature not used for selection. |
| w08 | ashburn-va | 2024-07-15T18:00:00Z | 2024-07-15T19:00:00Z | 0.9924236660242794 | 0.9924236660242794 | True | True | Largest minimum residual GPU capacity; temperature not used for selection. |
| w09 | phoenix-az | 2024-07-15T20:00:00Z | 2024-07-15T22:00:00Z | 2.0 | 1.0 | True | True | Largest minimum residual GPU capacity; temperature not used for selection. |
| w10 | atlanta-ga | 2024-07-15T21:00:00Z | 2024-07-15T22:00:00Z | 0.659293350099405 | 0.659293350099405 | True | True | Largest minimum residual GPU capacity; temperature not used for selection. |

### thermalshift

| Workload | Site | Start | End | Exposure | Mean stress | Deadline | Capacity | Reason |
|---|---|---|---|---:|---:|:---:|:---:|---|
| w01 | atlanta-ga | 2024-07-15T20:00:00Z | 2024-07-15T22:00:00Z | 1.6069902864171883 | 0.8034951432085942 | True | True | Constraint-aware thermal optimization after preserving maximum feasible workload completion. |
| w02 | atlanta-ga | 2024-07-15T20:00:00Z | 2024-07-15T22:00:00Z | 1.6069902864171883 | 0.8034951432085942 | True | True | Constraint-aware thermal optimization after preserving maximum feasible workload completion. |
| w03 | atlanta-ga | 2024-07-15T21:00:00Z | 2024-07-16T00:00:00Z | 2.0699712247028397 | 0.6899904082342799 | True | True | Constraint-aware thermal optimization after preserving maximum feasible workload completion. |
| w04 | atlanta-ga | 2024-07-15T21:00:00Z | 2024-07-15T22:00:00Z | 0.659293350099405 | 0.659293350099405 | True | True | Constraint-aware thermal optimization after preserving maximum feasible workload completion. |
| w05 | ashburn-va | 2024-07-15T21:00:00Z | 2024-07-15T23:00:00Z | 1.6098323012853117 | 0.8049161506426559 | True | True | Constraint-aware thermal optimization after preserving maximum feasible workload completion. |
| w06 | atlanta-ga | 2024-07-15T22:00:00Z | 2024-07-15T23:00:00Z | 0.67708168018729 | 0.67708168018729 | True | True | Constraint-aware thermal optimization after preserving maximum feasible workload completion. |
| w07 | atlanta-ga | 2024-07-15T22:00:00Z | 2024-07-16T00:00:00Z | 1.4106778746034347 | 0.7053389373017174 | True | True | Constraint-aware thermal optimization after preserving maximum feasible workload completion. |
| w08 | atlanta-ga | 2024-07-15T18:00:00Z | 2024-07-15T19:00:00Z | 0.9492478616154094 | 0.9492478616154094 | True | True | Constraint-aware thermal optimization after preserving maximum feasible workload completion. |
| w09 | san-antonio-tx | 2024-07-15T18:00:00Z | 2024-07-15T20:00:00Z | 1.9381480033682328 | 0.9690740016841164 | True | True | Constraint-aware thermal optimization after preserving maximum feasible workload completion. |
| w10 | atlanta-ga | 2024-07-15T23:00:00Z | 2024-07-16T00:00:00Z | 0.7335961944161448 | 0.7335961944161448 | True | True | Constraint-aware thermal optimization after preserving maximum feasible workload completion. |

## Methodology and fairness

All schedulers receive the same sites, workloads, capacity constraints, and thermal grid. Direct thermal percentages use the existing fairness gate and are available only when scheduled workload sets match.

## Scientific boundaries

Thermal stress-hours are a modeled scheduling metric derived from ambient-temperature inputs. They are not GPU temperature, server inlet temperature, PUE, cooling energy, electricity consumption, electricity savings, water consumption, water savings.

Ambient temperatures come from FortyGuard; workloads and GPU capacities are modeled benchmark parameters, not real customer workloads or facility telemetry.

## Reproducibility

Artifact schema: `1.0`. Sites and workloads are ID-sorted; scenario inputs, scheduler decisions, thermal metrics, and fairness comparisons are deterministic for identical inputs. JSON structure and key ordering are stable. Measured `runtime_ms` is observational and may vary by machine or execution; `generated_at_utc`, when supplied, is metadata.
