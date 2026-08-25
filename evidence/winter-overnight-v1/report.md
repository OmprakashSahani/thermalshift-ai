# ThermalShift Benchmark Report

## Evidence classification

FORTYGUARD-BACKED HISTORICAL REPLAY

REAL HISTORICAL AMBIENT TEMPERATURES + MODELED WORKLOADS

## Scenario

- Scenario ID: `fortyguard-winter-overnight-v1`
- Description: FortyGuard supplies real historical ambient-temperature observations; workload and 64-GPU capacity inputs are modeled benchmark parameters, not real facility telemetry.
- Data source: `FORTYGUARD_HISTORICAL_TEMPERATURES_WITH_MODELED_WORKLOADS`
- Generated at UTC: not supplied

## Calibration / provenance

- Replay window: `winter-overnight-v1` starting 2024-01-15T06:00:00Z
- Replay slots: 6
- Calibration: 28 observations; `pooled_p10_p90`
- Calibration references: 4.567570294117648°C / 37.01878625°C
- Request-time interpretation: AOI-local start_time; FortyGuard infers timezone and DST from AOI polygon coordinates; ThermalShift converts each orchestration UTC instant to the modeled site local time before submission

## Scheduler results

| Scheduler | Scheduled | Unscheduled | Completion | Deadline satisfaction | Stress-hours | Mean occupied stress | Peak occupied stress | Runtime ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| first_available | 10 | 0 | 100.0% | 100.0% | 0.152 | 0.009 | 0.070 | 2.637 |
| capacity_only | 10 | 0 | 100.0% | 100.0% | 0.168 | 0.010 | 0.070 | 3.840 |
| thermalshift | 10 | 0 | 100.0% | 100.0% | 0.000 | 0.000 | 0.000 | 20.317 |

## ThermalShift comparisons

- **ThermalShift vs First Available:** ThermalShift reduced modeled ambient thermal exposure by 100.0% versus First Available while preserving 100.0% deadline satisfaction.
- **ThermalShift vs Capacity Only:** ThermalShift reduced modeled ambient thermal exposure by 100.0% versus Capacity Only while preserving 100.0% deadline satisfaction.

**Interpretation note:** ThermalShift reaches the modeled thermal-stress floor in this replay. The 100% relative reduction means candidate stress-hours are 0.000 against positive baseline stress-hours (First Available: 0.152; Capacity Only: 0.168); it does not mean 100% cooling, energy, electricity, water, or facility savings.

## Scheduling decisions

### first_available

| Workload | Site | Start | End | Exposure | Mean stress | Deadline | Capacity | Reason |
|---|---|---|---|---:|---:|:---:|:---:|---|
| w01 | ashburn-va | 2024-01-15T06:00:00Z | 2024-01-15T08:00:00Z | 0.0 | 0.0 | True | True | Earliest feasible placement using stable site order; temperature not used for selection. |
| w02 | ashburn-va | 2024-01-15T06:00:00Z | 2024-01-15T08:00:00Z | 0.0 | 0.0 | True | True | Earliest feasible placement using stable site order; temperature not used for selection. |
| w03 | ashburn-va | 2024-01-15T06:00:00Z | 2024-01-15T09:00:00Z | 0.0 | 0.0 | True | True | Earliest feasible placement using stable site order; temperature not used for selection. |
| w04 | ashburn-va | 2024-01-15T07:00:00Z | 2024-01-15T08:00:00Z | 0.0 | 0.0 | True | True | Earliest feasible placement using stable site order; temperature not used for selection. |
| w05 | phoenix-az | 2024-01-15T07:00:00Z | 2024-01-15T09:00:00Z | 0.04839890017988691 | 0.024199450089943456 | True | True | Earliest feasible placement using stable site order; temperature not used for selection. |
| w06 | san-antonio-tx | 2024-01-15T08:00:00Z | 2024-01-15T09:00:00Z | 0.0 | 0.0 | True | True | Earliest feasible placement using stable site order; temperature not used for selection. |
| w07 | ashburn-va | 2024-01-15T08:00:00Z | 2024-01-15T10:00:00Z | 0.0 | 0.0 | True | True | Earliest feasible placement using stable site order; temperature not used for selection. |
| w08 | ashburn-va | 2024-01-15T06:00:00Z | 2024-01-15T07:00:00Z | 0.0 | 0.0 | True | True | Earliest feasible placement using stable site order; temperature not used for selection. |
| w09 | phoenix-az | 2024-01-15T06:00:00Z | 2024-01-15T08:00:00Z | 0.1031738122329989 | 0.05158690611649945 | True | True | Earliest feasible placement using stable site order; temperature not used for selection. |
| w10 | ashburn-va | 2024-01-15T09:00:00Z | 2024-01-15T10:00:00Z | 0.0 | 0.0 | True | True | Earliest feasible placement using stable site order; temperature not used for selection. |

### capacity_only

| Workload | Site | Start | End | Exposure | Mean stress | Deadline | Capacity | Reason |
|---|---|---|---|---:|---:|:---:|:---:|---|
| w01 | phoenix-az | 2024-01-15T06:00:00Z | 2024-01-15T08:00:00Z | 0.1031738122329989 | 0.05158690611649945 | True | True | Largest minimum residual GPU capacity; temperature not used for selection. |
| w02 | san-antonio-tx | 2024-01-15T06:00:00Z | 2024-01-15T08:00:00Z | 0.0 | 0.0 | True | True | Largest minimum residual GPU capacity; temperature not used for selection. |
| w03 | atlanta-ga | 2024-01-15T06:00:00Z | 2024-01-15T09:00:00Z | 0.04632657912027789 | 0.01544219304009263 | True | True | Largest minimum residual GPU capacity; temperature not used for selection. |
| w04 | ashburn-va | 2024-01-15T07:00:00Z | 2024-01-15T08:00:00Z | 0.0 | 0.0 | True | True | Largest minimum residual GPU capacity; temperature not used for selection. |
| w05 | ashburn-va | 2024-01-15T08:00:00Z | 2024-01-15T10:00:00Z | 0.0 | 0.0 | True | True | Largest minimum residual GPU capacity; temperature not used for selection. |
| w06 | san-antonio-tx | 2024-01-15T08:00:00Z | 2024-01-15T09:00:00Z | 0.0 | 0.0 | True | True | Largest minimum residual GPU capacity; temperature not used for selection. |
| w07 | san-antonio-tx | 2024-01-15T09:00:00Z | 2024-01-15T11:00:00Z | 0.0 | 0.0 | True | True | Largest minimum residual GPU capacity; temperature not used for selection. |
| w08 | ashburn-va | 2024-01-15T06:00:00Z | 2024-01-15T07:00:00Z | 0.0 | 0.0 | True | True | Largest minimum residual GPU capacity; temperature not used for selection. |
| w09 | phoenix-az | 2024-01-15T08:00:00Z | 2024-01-15T10:00:00Z | 0.015628604073630044 | 0.007814302036815022 | True | True | Largest minimum residual GPU capacity; temperature not used for selection. |
| w10 | atlanta-ga | 2024-01-15T09:00:00Z | 2024-01-15T10:00:00Z | 0.002503314154567681 | 0.002503314154567681 | True | True | Largest minimum residual GPU capacity; temperature not used for selection. |

### thermalshift

| Workload | Site | Start | End | Exposure | Mean stress | Deadline | Capacity | Reason |
|---|---|---|---|---:|---:|:---:|:---:|---|
| w01 | ashburn-va | 2024-01-15T06:00:00Z | 2024-01-15T08:00:00Z | 0.0 | 0.0 | True | True | Constraint-aware thermal optimization after preserving maximum feasible workload completion. |
| w02 | ashburn-va | 2024-01-15T06:00:00Z | 2024-01-15T08:00:00Z | 0.0 | 0.0 | True | True | Constraint-aware thermal optimization after preserving maximum feasible workload completion. |
| w03 | ashburn-va | 2024-01-15T06:00:00Z | 2024-01-15T09:00:00Z | 0.0 | 0.0 | True | True | Constraint-aware thermal optimization after preserving maximum feasible workload completion. |
| w04 | ashburn-va | 2024-01-15T07:00:00Z | 2024-01-15T08:00:00Z | 0.0 | 0.0 | True | True | Constraint-aware thermal optimization after preserving maximum feasible workload completion. |
| w05 | ashburn-va | 2024-01-15T08:00:00Z | 2024-01-15T10:00:00Z | 0.0 | 0.0 | True | True | Constraint-aware thermal optimization after preserving maximum feasible workload completion. |
| w06 | san-antonio-tx | 2024-01-15T08:00:00Z | 2024-01-15T09:00:00Z | 0.0 | 0.0 | True | True | Constraint-aware thermal optimization after preserving maximum feasible workload completion. |
| w07 | ashburn-va | 2024-01-15T08:00:00Z | 2024-01-15T10:00:00Z | 0.0 | 0.0 | True | True | Constraint-aware thermal optimization after preserving maximum feasible workload completion. |
| w08 | ashburn-va | 2024-01-15T06:00:00Z | 2024-01-15T07:00:00Z | 0.0 | 0.0 | True | True | Constraint-aware thermal optimization after preserving maximum feasible workload completion. |
| w09 | san-antonio-tx | 2024-01-15T06:00:00Z | 2024-01-15T08:00:00Z | 0.0 | 0.0 | True | True | Constraint-aware thermal optimization after preserving maximum feasible workload completion. |
| w10 | ashburn-va | 2024-01-15T09:00:00Z | 2024-01-15T10:00:00Z | 0.0 | 0.0 | True | True | Constraint-aware thermal optimization after preserving maximum feasible workload completion. |

## Methodology and fairness

All schedulers receive the same sites, workloads, capacity constraints, and thermal grid. Direct thermal percentages use the existing fairness gate and are available only when scheduled workload sets match.

## Scientific boundaries

Thermal stress-hours are a modeled scheduling metric derived from ambient-temperature inputs. They are not GPU temperature, server inlet temperature, PUE, cooling energy, electricity consumption, electricity savings, water consumption, water savings.

Ambient temperatures come from FortyGuard; workloads and GPU capacities are modeled benchmark parameters, not real customer workloads or facility telemetry.

## Reproducibility

Artifact schema: `1.0`. Sites and workloads are ID-sorted; scenario inputs, scheduler decisions, thermal metrics, and fairness comparisons are deterministic for identical inputs. JSON structure and key ordering are stable. Measured `runtime_ms` is observational and may vary by machine or execution; `generated_at_utc`, when supplied, is metadata.
