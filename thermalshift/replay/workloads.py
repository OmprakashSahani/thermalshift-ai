"""Fixed modeled workloads for historical replay benchmarks."""

from datetime import timedelta

from thermalshift.domain.models import Workload, WorkloadPriority
from thermalshift.domain.sites import get_default_sites

from .models import HistoricalReplayWindow


def build_replay_workloads(window: HistoricalReplayWindow) -> tuple[Workload, ...]:
    """Build ten outcome-independent modeled workloads relative to a replay window."""
    site_ids = tuple(site.site_id for site in get_default_sites())
    all_sites = frozenset(site_ids)
    specifications = (
        ("w01", "Distributed training warmup", 16, 2, 0, 4, all_sites),
        ("w02", "Batch inference refresh", 24, 2, 0, 4, all_sites),
        ("w03", "Model evaluation suite", 16, 3, 0, 6, all_sites),
        ("w04", "Embedding index update", 8, 1, 1, 4, all_sites),
        ("w05", "Regional fine-tuning run", 32, 2, 1, 5, frozenset(site_ids[:2])),
        ("w06", "Regional inference batch", 24, 1, 2, 5, frozenset(site_ids[2:])),
        ("w07", "Checkpoint validation", 16, 2, 2, 6, all_sites),
        ("w08", "Urgent quality check", 8, 1, 0, 2, frozenset((site_ids[0], site_ids[3]))),
        ("w09", "Dataset feature extraction", 24, 2, 0, 5, frozenset(site_ids[1:3])),
        ("w10", "Late-window inference run", 16, 1, 3, 6, all_sites),
    )
    return tuple(
        Workload(
            workload_id=workload_id,
            name=name,
            gpu_demand=gpu_demand,
            duration_hours=duration,
            release_time=window.start_utc + timedelta(hours=release_offset),
            deadline=window.start_utc + timedelta(hours=deadline_offset),
            priority=WorkloadPriority.MEDIUM,
            eligible_site_ids=eligible_sites,
        )
        for (
            workload_id,
            name,
            gpu_demand,
            duration,
            release_offset,
            deadline_offset,
            eligible_sites,
        ) in specifications
    )
