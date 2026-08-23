"""Tests for the UTC-normalized hourly thermal scheduling grid."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from thermalshift.scheduler.grid import ThermalGrid, ThermalGridEntry, ThermalGridError


def entry(site_id: str, hour: int, score: float) -> ThermalGridEntry:
    return ThermalGridEntry(site_id, datetime(2024, 1, 1, hour, tzinfo=UTC), score)


def test_valid_lookup_and_available_timestamps() -> None:
    grid = ThermalGrid([entry("site-a", 1, 0.25), entry("site-a", 0, 0.5)])

    assert grid.get_score("site-a", datetime(2024, 1, 1, 0, tzinfo=UTC)) == 0.5
    assert grid.available_timestamps("site-a") == (
        datetime(2024, 1, 1, 0, tzinfo=UTC),
        datetime(2024, 1, 1, 1, tzinfo=UTC),
    )


def test_timezone_equivalent_lookup_normalizes_to_utc() -> None:
    grid = ThermalGrid([entry("site-a", 5, 0.4)])
    eastern = timezone(timedelta(hours=-5))

    assert grid.get_score("site-a", datetime(2024, 1, 1, 0, tzinfo=eastern)) == 0.4


def test_naive_timestamp_is_rejected() -> None:
    with pytest.raises(ThermalGridError, match="timezone-aware"):
        ThermalGrid([ThermalGridEntry("site-a", datetime(2024, 1, 1), 0.5)])


def test_non_hour_timestamp_is_rejected() -> None:
    with pytest.raises(ThermalGridError, match="exact hour"):
        ThermalGrid([ThermalGridEntry("site-a", datetime(2024, 1, 1, 0, 1, tzinfo=UTC), 0.5)])


@pytest.mark.parametrize("score", [-0.1, 1.1, float("nan"), float("inf")])
def test_invalid_score_is_rejected(score: float) -> None:
    with pytest.raises(ThermalGridError, match="finite and in"):
        ThermalGrid([entry("site-a", 0, score)])


def test_duplicate_normalized_key_is_rejected() -> None:
    eastern = timezone(timedelta(hours=-5))
    entries = [
        entry("site-a", 5, 0.2),
        ThermalGridEntry("site-a", datetime(2024, 1, 1, 0, tzinfo=eastern), 0.3),
    ]

    with pytest.raises(ThermalGridError, match="duplicate normalized"):
        ThermalGrid(entries)


def test_candidate_average_and_exposure_are_correct() -> None:
    grid = ThermalGrid([entry("site-a", 0, 0.25), entry("site-a", 1, 0.75)])

    metrics = grid.placement_metrics("site-a", datetime(2024, 1, 1, tzinfo=UTC), 2)

    assert metrics is not None
    assert metrics.scores == (0.25, 0.75)
    assert metrics.average_stress == pytest.approx(0.5)
    assert metrics.exposure_stress_hours == pytest.approx(1.0)


def test_missing_required_slot_makes_candidate_unavailable() -> None:
    grid = ThermalGrid([entry("site-a", 0, 0.25)])

    assert grid.placement_metrics("site-a", datetime(2024, 1, 1, tzinfo=UTC), 2) is None
