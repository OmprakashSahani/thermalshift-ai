"""Tests for the offline historical collection plan."""

from pathlib import Path

from examples.collect_historical import build_collection_plan, get_calibration_instants
from thermalshift.fortyguard.cache import HeatmapResultCache


def test_default_plan_has_four_sites_times_seven_instants(tmp_path: Path) -> None:
    entries = build_collection_plan(HeatmapResultCache(tmp_path))

    assert len(entries) == 28
    assert len({entry.site_id for entry in entries}) == 4
    assert len({entry.requested_utc for entry in entries}) == 7
    assert all(not entry.cache_hit for entry in entries)


def test_instants_are_unique_2024_utc_values_with_varied_hours() -> None:
    instants = get_calibration_instants()

    assert len(instants) == len(set(instants)) == 7
    assert all(instant.year == 2024 for instant in instants)
    assert all(instant.utcoffset().total_seconds() == 0 for instant in instants)
    assert len({instant.hour for instant in instants}) == 7
