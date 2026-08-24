"""Offline synthetic data for demonstrating scheduler behavior."""

from datetime import UTC, datetime, timedelta

from thermalshift.domain.models import Workload, WorkloadPriority
from thermalshift.domain.sites import get_default_sites
from thermalshift.scheduler.grid import ThermalGrid, ThermalGridEntry

from .models import BenchmarkScenario


def create_synthetic_scenario() -> BenchmarkScenario:
    """Return a deterministic, fully synthetic one-hour benchmark scenario."""
    sites = get_default_sites()
    start = datetime(2026, 7, 15, 12, tzinfo=UTC)
    site_offsets = (0.00, 0.04, 0.08, 0.12)
    hourly_base = (0.82, 0.74, 0.58, 0.22, 0.16, 0.20, 0.32, 0.45)
    entries = tuple(
        ThermalGridEntry(
            site_id=site.site_id,
            timestamp=start + timedelta(hours=hour),
            score=min(1.0, hourly_base[hour] + site_offsets[site_index]),
        )
        for site_index, site in enumerate(sites)
        for hour in range(len(hourly_base))
    )
    specifications = (
        ("a", 4, 1, 5, (0, 1)),
        ("b", 8, 2, 6, (0, 2)),
        ("c", 12, 1, 5, (0, 1, 2)),
        ("d", 6, 3, 7, (1, 2, 3)),
        ("e", 10, 2, 7, (0, 3)),
        ("f", 4, 1, 4, (0, 1, 2, 3)),
        ("g", 8, 2, 6, (1, 3)),
        ("h", 6, 1, 7, (0, 2, 3)),
    )
    workloads = tuple(
        Workload(
            workload_id=f"synthetic-{identifier}",
            name=f"Synthetic workload {identifier.upper()}",
            gpu_demand=gpu_demand,
            duration_hours=duration,
            release_time=start,
            deadline=start + timedelta(hours=deadline_offset),
            priority=WorkloadPriority.MEDIUM,
            eligible_site_ids=frozenset(sites[index].site_id for index in eligible),
        )
        for identifier, gpu_demand, duration, deadline_offset, eligible in specifications
    )
    return BenchmarkScenario(
        scenario_id="offline-synthetic-v1",
        description="Deterministic synthetic thermal-stress scheduler demonstration.",
        sites=sites,
        workloads=workloads,
        thermal_grid=ThermalGrid(entries),
        data_source_label="SYNTHETIC",
    )
