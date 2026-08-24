"""Offline adapters from cached FortyGuard results to benchmark inputs."""

from thermalshift.benchmark.models import BenchmarkScenario
from thermalshift.domain.models import Site, TemperatureObservation
from thermalshift.domain.sites import get_default_sites
from thermalshift.fortyguard.cache import HeatmapResultCache
from thermalshift.fortyguard.payloads import build_historical_heatmap_payload
from thermalshift.scheduler.grid import ThermalGrid, ThermalGridEntry
from thermalshift.thermal.calibration import calculate_calibration_diagnostics
from thermalshift.thermal.model import ThermalStressModel

from .models import (
    CalibrationStatus,
    HistoricalReplayWindow,
    ReplayDataIncompleteError,
    ReplayPlanEntry,
)
from .plan import build_calibration_plan, build_replay_plan
from .workloads import build_replay_workloads

CALIBRATION_EXPECTED_COUNT = 28
HISTORICAL_DATA_SOURCE_LABEL = (
    "FORTYGUARD_HISTORICAL_TEMPERATURES_WITH_MODELED_WORKLOADS"
)


def load_calibration_status(cache: HeatmapResultCache) -> CalibrationStatus:
    """Load available original calibration results and frozen P10/P90 diagnostics."""
    entries = build_calibration_plan(cache)
    observations, missing = _load_entries(entries, cache)
    diagnostics = (
        calculate_calibration_diagnostics(observations) if observations else None
    )
    lower = diagnostics.p10_c if diagnostics else None
    upper = diagnostics.p90_c if diagnostics else None
    reference_error = None
    if lower is not None and upper is not None and not upper > lower:
        reference_error = "pooled P10/P90 references must be distinct and ordered"
        lower = None
        upper = None
    return CalibrationStatus(
        expected_count=CALIBRATION_EXPECTED_COUNT,
        observations=observations,
        missing_entries=missing,
        diagnostics=diagnostics,
        lower_reference_c=lower,
        upper_reference_c=upper,
        reference_error=reference_error,
    )


def load_replay_observations(
    window: HistoricalReplayWindow, cache: HeatmapResultCache
) -> tuple[TemperatureObservation, ...]:
    """Load a complete replay window from cache or report every missing request."""
    plan = build_replay_plan(window, cache)
    observations, missing = _load_entries(plan.entries, cache)
    if missing:
        raise ReplayDataIncompleteError(
            "replay", len(plan.entries), len(observations), missing
        )
    return observations


def build_historical_thermal_grid(
    window: HistoricalReplayWindow, cache: HeatmapResultCache
) -> ThermalGrid:
    """Build a stress-score grid from complete calibration and replay cache data."""
    calibration = load_calibration_status(cache)
    if not calibration.official_ready:
        raise ReplayDataIncompleteError(
            "calibration",
            calibration.expected_count,
            calibration.available_count,
            calibration.missing_entries,
            detail=calibration.reference_error,
        )
    observations = load_replay_observations(window, cache)
    model = ThermalStressModel(
        lower_reference_c=calibration.lower_reference_c,
        upper_reference_c=calibration.upper_reference_c,
    )
    return ThermalGrid(
        ThermalGridEntry(
            site_id=assessment.site_id,
            timestamp=assessment.timestamp,
            score=assessment.thermal_stress_score,
        )
        for assessment in (model.assess(item) for item in observations)
    )


def build_historical_replay_scenario(
    window: HistoricalReplayWindow, cache: HeatmapResultCache
) -> BenchmarkScenario:
    """Build an official-ready cache-only FortyGuard historical replay scenario."""
    return BenchmarkScenario(
        scenario_id=f"fortyguard-{window.window_id}",
        description=(
            "FortyGuard supplies real historical ambient-temperature observations; "
            "workload and 64-GPU capacity inputs are modeled benchmark parameters, "
            "not real facility telemetry."
        ),
        sites=get_default_sites(),
        workloads=build_replay_workloads(window),
        thermal_grid=build_historical_thermal_grid(window, cache),
        data_source_label=HISTORICAL_DATA_SOURCE_LABEL,
    )


def _load_entries(
    entries: tuple[ReplayPlanEntry, ...], cache: HeatmapResultCache
) -> tuple[tuple[TemperatureObservation, ...], tuple[ReplayPlanEntry, ...]]:
    sites: dict[str, Site] = {site.site_id: site for site in get_default_sites()}
    observations: list[TemperatureObservation] = []
    missing: list[ReplayPlanEntry] = []
    for entry in entries:
        payload = build_historical_heatmap_payload(
            sites[entry.site_id], entry.requested_utc
        )
        result = cache.get(payload)
        if result is None:
            missing.append(entry)
            continue
        observations.append(
            TemperatureObservation(
                site_id=entry.site_id,
                timestamp=entry.requested_utc,
                temperature_c=result.stats_data.temperature_stats.mean,
                source="fortyguard",
                observation_type="historical",
            )
        )
    return tuple(observations), tuple(missing)
